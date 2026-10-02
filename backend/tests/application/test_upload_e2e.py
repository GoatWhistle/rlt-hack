from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.adapter.repository.clickhouse.migrator import MIGRATION_DIR, Migrator
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.application.api import ApiContainer
from src.application.config import AppConfig, UploadConfig
from src.controller.http.app import create_app
from src.controller.http.settings import ApiSettings
from tests.adapter.repository.seed import Seeder
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.fakes.domain import make_offer, make_source, make_supplier
from tests.fakes.waiting import eventually

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb

ALPHA = make_supplier("alpha", inn="7801234564")
GAMMA = make_supplier("gamma", inn=None)
NOTICES = "\n".join(
    (
        "lot_id;procedure_name;subject;start_price;publish_date",
        '101;Поставка крупы;"Крупа гречневая ядрица 500 кг; рис шлифованный 200 кг";'
        "1500,00;2024-01-18",
        "102;Оказание услуг связи;;;",
        "bad id;Без номера;;;",
    )
)


async def seed(gateway: ChdbGateway) -> None:
    seeder = Seeder(gateway)
    await seeder.suppliers(ALPHA, GAMMA)
    await seeder.sources(make_source())
    buckwheat = replace(make_offer("buckwheat", supplier=ALPHA), name="Крупа гречневая ядрица")
    rice = replace(make_offer("rice", supplier=ALPHA), name="Рис шлифованный")
    await seeder.offers(buckwheat, rice)
    await seeder.lot("L1", "Поставка крупы гречневой для школ")
    await seeder.participation("L1", GAMMA, won=True)


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    engine = pytest.importorskip("chdb.session")
    session = engine.Session(str(tmp_path / "chdb"))
    gateway = ChdbGateway(session)
    await Migrator(gateway, MIGRATION_DIR).apply_pending()
    await seed(gateway)

    async def connect() -> SqlGateway:
        return gateway

    config = AppConfig(upload=UploadConfig(concurrency=2))
    app = create_app(ApiContainer(config, connect), ApiSettings())
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
    session.close()


async def finished(client: httpx.AsyncClient, location: str) -> Any:
    async def done() -> bool:
        detail = (await client.get(location)).json()
        return bool(detail["processed"] == detail["total"])

    await eventually(done)
    return (await client.get(location)).json()


async def uploaded(client: httpx.AsyncClient) -> Any:
    files = {"file": ("закупки.csv", NOTICES.encode("cp1251"), "text/csv")}
    created = await client.post("/api/uploads", files=files)
    assert created.status_code == 201
    assert (created.json()["total"], created.json()["rejected"]) == (2, 1)
    return await finished(client, created.headers["Location"])


async def test_csv_becomes_lots_with_candidates(client: httpx.AsyncClient) -> None:
    detail = await uploaded(client)
    assert [lot["id"] for lot in detail["lots"]] == ["101", "102"]
    assert detail["lots"][0]["searchId"] is not None
    assert detail["issues"] == [{"row": 4, "code": "badLotId", "value": "bad id"}]
    lot = (await client.get(f"/api/uploads/{detail['id']}/lots/101")).json()
    search = lot["search"]
    assert lot["lot"]["searchId"] == search["searchId"]
    assert (search["query"]["origin"], search["query"]["context"]["startPrice"]) == (
        "upload",
        "1500.00",
    )
    assert [item["name"] for item in search["items"]] == [
        "Крупа гречневая ядрица",
        "Рис шлифованный",
    ]
    assert search["candidates"][0]["inn"] == "7801234564"
    assert {match["basis"] for match in search["candidates"][0]["matches"]} == {"stock"}
    assert lot["lot"]["status"] == detail["lots"][0]["status"]
    assert lot["upload"]["fileName"] == "закупки.csv"
    results = await client.post(
        f"/api/uploads/{detail['id']}/results", json={"lotIds": ["101", "102"]}
    )
    assert [entry["lot"]["id"] for entry in results.json()["results"]] == ["101", "102"]


async def test_lot_equals_manual_search_and_stays_private(client: httpx.AsyncClient) -> None:
    detail = await uploaded(client)
    search = (await client.get(f"/api/uploads/{detail['id']}/lots/101")).json()["search"]
    manual = (await client.post("/api/searches", json={"text": search["query"]["text"]})).json()
    assert [entry["id"] for entry in manual["candidates"]] == [
        entry["id"] for entry in search["candidates"]
    ]
    assert [entry["matches"] for entry in manual["candidates"]] == [
        entry["matches"] for entry in search["candidates"]
    ]
    recent = (await client.get("/api/searches")).json()["searches"]
    assert [entry["searchId"] for entry in recent] == [manual["searchId"]]
    assert (await client.get("/api/uploads")).json()["uploads"][0]["id"] == detail["id"]
    client.cookies.clear()
    assert (await client.get("/api/uploads")).json()["uploads"] == []
    other = await client.get(f"/api/uploads/{detail['id']}")
    assert (other.status_code, other.json()["code"]) == (404, "upload_not_found")


async def test_broken_file_is_rejected(client: httpx.AsyncClient) -> None:
    files = {"file": ("notices.csv", b"lot_id;subject\n1;x", "text/csv")}
    response = await client.post("/api/uploads", files=files)
    assert (response.status_code, response.json()["code"]) == (422, "missing_columns")
