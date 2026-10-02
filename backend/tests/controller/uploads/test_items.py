from dataclasses import replace
from decimal import Decimal

import httpx
import pytest

from src.controller.uploads.item_file import read_positions
from src.models.errors import InvalidNoticeRowError, MissingNoticeColumnsError
from src.models.operations.upload import Notice
from tests.controller.uploads.conftest import CSV, FakeEngine

ITEMS = "lot_id;product_name;okpd2_code\nL1;Вода питьевая;11.07.11\nL1;Стаканы;22.29\n".encode()


async def test_both_files_reach_search_and_survive_storage(
    search_client: httpx.AsyncClient,
) -> None:
    response = await search_client.post(
        "/api/uploads",
        files={"file": ("notices.csv", CSV), "items_file": ("items.csv", ITEMS)},
    )
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["fileName"] == "notices.csv + items.csv"
    result = await search_client.get(f"/api/uploads/{summary['id']}/lots/L1")
    products = result.json()["recommendation"]["products"]
    assert [product["name"] for product in products] == ["Вода питьевая", "Стаканы"]
    assert [product["okpd2"] for product in products] == ["11.07.11", "22.29"]
    assert result.json()["lot"]["products"] == 2
    assert all(product["origin"] == "notice" for product in products)


async def test_query_uses_items_codes_and_keeps_context() -> None:
    notice = Notice("L1", "Закупка", customer_inn="7801234564", start_price=Decimal(100))
    enriched = (await read_positions([notice], ITEMS))[0]
    assert enriched.customer_inn == notice.customer_inn
    assert enriched.start_price == notice.start_price
    assert all(
        text in enriched.query_text
        for text in ("Закупка", "Вода питьевая", "Стаканы", "11.07.11", "22.29")
    )
    assert (
        replace(enriched, positions=tuple(reversed(enriched.positions))).query_text
        == enriched.query_text
    )


async def test_duplicate_input_positions_are_preserved_without_query_repetition() -> None:
    data = b"lot_id;product_name;okpd2_code\nL1;water;11.07\nL1;water;11.07\n"
    enriched = (await read_positions([Notice("L1", "query")], data))[0]
    assert len(enriched.positions) == 2
    assert len({item.item_id for item in enriched.positions}) == 2
    assert enriched.query_text.count("water") == 1


async def test_orphan_items_fail_before_ranking(
    search_client: httpx.AsyncClient, engine: FakeEngine
) -> None:
    response = await search_client.post(
        "/api/uploads",
        files={
            "file": ("notices.csv", CSV),
            "items_file": ("items.csv", ITEMS.replace(b"L1", b"L2")),
        },
    )
    assert response.status_code == 422
    assert engine.calls == 0


@pytest.mark.parametrize(
    ("data", "error"),
    [
        (b"lot_id;name\nL1;water\n", MissingNoticeColumnsError),
        (b"lot_id;product_name;okpd2_code\nL1;;11.07\n", InvalidNoticeRowError),
        (b"lot_id;product_name;okpd2_code\nL1;water;bad\n", InvalidNoticeRowError),
    ],
)
async def test_invalid_items_are_explicit(data: bytes, error: type[Exception]) -> None:
    with pytest.raises(error):
        await read_positions([Notice("L1", "query")], data)
