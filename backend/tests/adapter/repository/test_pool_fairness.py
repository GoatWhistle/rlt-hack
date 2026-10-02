import asyncio
import time

import pytest

from src.adapter.repository.clickhouse.engine.gateway import ConnectGateway
from src.adapter.repository.clickhouse.engine.pool.gateway import GatewayPool, fair_share
from tests.adapter.repository.pool_fakes import Driver, FakeDriver, select_many

QUERY_SECONDS = 0.05


async def scoped_search(pool: GatewayPool, items: int) -> float:
    async with pool.scope():
        started = time.perf_counter()
        await select_many(pool, items)
        return time.perf_counter() - started


@pytest.mark.parametrize(("size", "share"), [(1, 1), (2, 1), (3, 2), (4, 2), (8, 4)])
def test_one_scope_gets_half_of_the_pool(size: int, share: int) -> None:
    assert fair_share(size) == share
    assert GatewayPool(Driver().open, size).share == share
    assert GatewayPool(Driver().open, size, share=10).share == size


def test_share_must_be_positive() -> None:
    with pytest.raises(ValueError, match="0"):
        GatewayPool(Driver().open, 4, share=0)


async def test_scope_bounds_concurrency_of_one_search() -> None:
    driver = Driver()
    driver.activity.delay = 0.01
    pool = GatewayPool(driver.open, 4)
    await scoped_search(pool, 12)
    assert driver.activity.peak == 2
    await select_many(pool, 12)
    assert driver.activity.peak == 4


async def test_small_search_not_starved_by_large() -> None:
    driver = Driver()
    driver.activity.delay = QUERY_SECONDS
    pool = GatewayPool(driver.open, 4)
    large = asyncio.create_task(scoped_search(pool, 50))
    await asyncio.sleep(QUERY_SECONDS / 2)
    small = await scoped_search(pool, 1)
    assert small < 2 * QUERY_SECONDS + 0.05
    assert not large.done()
    await large


async def test_scope_of_another_pool_does_not_limit() -> None:
    driver = Driver()
    driver.activity.delay = 0.01
    first = GatewayPool(driver.open, 4)
    second = GatewayPool(Driver().open, 4)
    async with second.scope():
        await select_many(first, 8)
    assert driver.activity.peak == 4


async def test_insert_describes_table_once() -> None:
    driver = FakeDriver(Driver().activity, 0)
    driver.activity.delay = 0
    gateway = ConnectGateway(driver)
    for value in range(3):
        await gateway.insert("db.searches", ("search_id", "text"), [(value, "x")])
    await gateway.insert("db.uploads", ("upload_id",), [(1,)])
    assert driver.described == ["db.searches", "db.uploads"]
    assert driver.inserted_types[1:3] == [("type:search_id", "type:text")] * 2
    assert all(query_id for query_id in driver.query_ids)
