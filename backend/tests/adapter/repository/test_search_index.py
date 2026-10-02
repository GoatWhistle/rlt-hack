from dataclasses import replace

import pytest

from src.adapter.repository.clickhouse.search.retrieval.prefixes import prefix_terms
from tests.adapter.repository.seed import DATABASE, Seeder
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.fakes.domain import make_offer, make_source, make_supplier

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb

ALPHA = make_supplier("alpha", inn="7801234564")
EXPLAIN = (
    "EXPLAIN indexes = 1 SELECT {column} FROM {table} WHERE hasAnyTokens({expression}, [{term}])"
)


async def selected_granules(gateway: ChdbGateway, table: str, column: str, term: str) -> str:
    rows = await gateway.select(
        EXPLAIN.format(
            column=column, table=table, expression=prefix_terms(column), term=f"'{term}'"
        )
    )
    plan = [str(row[0]).strip() for row in rows]
    position = next(index for index, line in enumerate(plan) if line.startswith("Name: idx_"))
    return next(line for line in plan[position:] if line.startswith("Granules:"))


async def test_absent_term_selects_no_offer_granules(gateway: ChdbGateway) -> None:
    seeder = Seeder(gateway)
    await seeder.suppliers(ALPHA)
    await seeder.sources(make_source())
    await seeder.offers(replace(make_offer("buckwheat", supplier=ALPHA), name="Крупа гречневая"))
    table = f"{DATABASE}.offers"
    assert (await selected_granules(gateway, table, "search_text", "зщзщзщ")).startswith(
        "Granules: 0/"
    )
    assert not (await selected_granules(gateway, table, "search_text", "круп")).startswith(
        "Granules: 0/"
    )


async def test_absent_term_selects_no_lot_granules(gateway: ChdbGateway) -> None:
    seeder = Seeder(gateway)
    await seeder.suppliers(ALPHA)
    await seeder.lot("L1", "Поставка крупы гречневой")
    await seeder.participation("L1", ALPHA, won=True)
    await seeder.refresh_history()
    table = f"{DATABASE}.lot_texts"
    granules = await selected_granules(gateway, table, "text", "зщзщ")
    assert granules.startswith("Granules: 0/")
    rows = await gateway.select(f"SELECT lot_id, title, terms FROM {table}")
    assert rows == [("L1", "Поставка крупы гречневой", 4)]


async def test_search_archive_retains_history(gateway: ChdbGateway) -> None:
    rows = await gateway.select(
        f"SELECT engine_full FROM system.tables WHERE database = '{DATABASE}' AND name = 'searches'"
    )
    [(engine,)] = rows
    assert "TTL" not in str(engine)
    assert "ReplacingMergeTree(version)" in str(engine)
