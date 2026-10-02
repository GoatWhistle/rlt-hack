import time
from collections.abc import Callable

from bench import catalog, procurement
from bench.clickhouse import ClickHouseHttp
from bench.sql import DB, Volume

TABLES = (
    "suppliers",
    "sources",
    "offers",
    "catalog_items",
    "offer_matches",
    "procurement_lots",
    "procurement_items",
    "lot_participations",
    "searches",
)
SEED_SETTINGS = {"max_query_size": "10000000", "max_insert_threads": "4"}
REFRESHED_VIEWS = ("lot_texts_refresh", "supplier_lots_refresh")


def _statements(volume: Volume) -> list[tuple[str, Callable[[], str]]]:
    return [
        ("suppliers", lambda: catalog.suppliers(volume)),
        ("sources", lambda: catalog.sources(volume)),
        ("offers", lambda: catalog.offers(volume)),
        ("catalog_items", catalog.catalog_items),
        ("offer_matches", lambda: catalog.offer_matches(volume)),
        ("procurement_lots", lambda: procurement.lots(volume)),
        ("procurement_items", lambda: procurement.items(volume)),
        ("lot_participations", lambda: procurement.participations(volume)),
    ]


async def counts(clickhouse: ClickHouseHttp) -> dict[str, int]:
    found: dict[str, int] = {}
    for table in TABLES:
        found[table] = await clickhouse.scalar(f"SELECT count() FROM {DB}.{table} FINAL")
    return found


async def seed(clickhouse: ClickHouseHttp, volume: Volume, reset: bool) -> dict[str, float]:
    if reset:
        for table in TABLES:
            await clickhouse.execute(f"TRUNCATE TABLE IF EXISTS {DB}.{table}")
    elif (await counts(clickhouse))["offers"] >= volume.offers:
        return {}
    timings: dict[str, float] = {}
    for table, statement in _statements(volume):
        started = time.perf_counter()
        await clickhouse.execute(statement(), SEED_SETTINGS)
        await clickhouse.execute(f"OPTIMIZE TABLE {DB}.{table} FINAL")
        timings[table] = round(time.perf_counter() - started, 2)
    for view in REFRESHED_VIEWS:
        started = time.perf_counter()
        await clickhouse.execute(f"SYSTEM REFRESH VIEW {DB}.{view}")
        await clickhouse.execute(f"SYSTEM WAIT VIEW {DB}.{view}")
        timings[view] = round(time.perf_counter() - started, 2)
    return timings
