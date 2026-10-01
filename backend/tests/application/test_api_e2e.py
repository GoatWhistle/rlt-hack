from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from src.adapter.repository.clickhouse.migrator import MIGRATION_DIR, Migrator
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.application.api import ApiContainer
from src.application.config import AppConfig
from src.controller.http.app import create_app
from src.controller.http.settings import ApiSettings
from tests.adapter.repository.seed import Seeder
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.fakes.domain import make_offer, make_source, make_supplier

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb

ALPHA = make_supplier("alpha", inn="7801234564")
GAMMA = make_supplier("gamma", inn=None)


async def seed(gateway: ChdbGateway) -> None:
    seeder = Seeder(gateway)
    await seeder.suppliers(ALPHA, GAMMA)
    await seeder.sources(make_source())
    buckwheat = replace(make_offer("buckwheat", supplier=ALPHA), name="Крупа гречневая ядрица")
    rice = replace(make_offer("rice", supplier=ALPHA), name="Рис шлифованный")
    await seeder.offers(buckwheat, rice)
    await seeder.match(rice.offer_id, "accepted")
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

    app = create_app(ApiContainer(AppConfig(), connect), ApiSettings())
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield http
    session.close()


async def test_text_search_runs_through_http_and_reopens(client: httpx.AsyncClient) -> None:
    text = "Крупа гречневая ядрица 500 кг; рис шлифованный 200 кг"
    created = await client.post(
        "/api/searches", json={"text": text}, headers={"Accept-Language": "en"}
    )
    assert created.status_code == 201
    body = created.json()
    assert body["query"]["locale"] == "en"
    assert [item["quantity"]["value"] for item in body["items"]] == ["500", "200"]
    alpha, gamma = body["candidates"]
    assert (alpha["inn"], alpha["status"], alpha["checkReasons"]) == (
        "7801234564",
        "recommended",
        [],
    )
    assert {match["basis"] for match in alpha["matches"]} == {"stock"}
    assert gamma["inn"] == ""
    assert "innMissing" in gamma["checkReasons"]
    assert gamma["history"]["wins"] == 1
    reopened = await client.get(created.headers["Location"])
    assert reopened.json() == body
    recent = (await client.get("/api/searches?limit=5")).json()["searches"]
    assert recent[0]["searchId"] == body["searchId"]


async def test_supplier_profile_and_readiness_use_the_same_storage(
    client: httpx.AsyncClient,
) -> None:
    profile = await client.get(f"/api/suppliers/{ALPHA.supplier_id}")
    assert profile.status_code == 200
    assert profile.json()["role"] == "distributor"
    assert len(profile.json()["offers"]) == 2
    missing = await client.get(f"/api/suppliers/{make_supplier('nobody').supplier_id}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "supplier_not_found"
    ready = await client.get("/api/health/ready")
    assert ready.json()["ready"] is True
