import asyncio
import threading
import time

import pytest
from clickhouse_connect.driver.exceptions import DatabaseError, OperationalError

from src.adapter.repository.clickhouse.engine.pool.gateway import GatewayPool
from src.adapter.repository.errors import RepositoryError, RepositoryUnavailableError
from tests.adapter.repository.pool_fakes import Driver, select_many, transport_error


async def test_clients_open_lazily_and_are_reused_sequentially() -> None:
    driver = Driver()
    pool = GatewayPool(driver.open, 4)
    assert (pool.size, pool.opened) == (4, 0)
    for index in range(3):
        assert await pool.select(f"SELECT {index}") == [(0, f"SELECT {index}")]
    await pool.command("OPTIMIZE")
    await pool.insert("t", ("a",), [(1,)])
    await pool.insert("t", ("a",), [])
    assert pool.opened == 1
    assert driver.drivers[0].statements == ["SELECT 0", "SELECT 1", "SELECT 2", "OPTIMIZE", "t"]


@pytest.mark.parametrize("size", [1, 4])
async def test_concurrency_is_bounded_by_pool_size(size: int) -> None:
    driver = Driver()
    pool = GatewayPool(driver.open, size)
    rows = await select_many(pool, 12)
    assert [row[0][1] for row in rows] == [f"SELECT {index}" for index in range(12)]
    assert driver.activity.peak == size
    assert pool.opened == size


async def test_pool_runs_queries_in_parallel() -> None:
    driver = Driver()
    driver.activity.delay = 0.1
    started = time.perf_counter()
    await select_many(GatewayPool(driver.open, 4), 4)
    assert time.perf_counter() - started < 0.35


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (OSError("reset"), RepositoryUnavailableError),
        (transport_error(), RepositoryUnavailableError),
        (OperationalError("Code: 159. TIMEOUT_EXCEEDED"), RepositoryError),
        (DatabaseError("bad sql"), RepositoryError),
        (ValueError("other"), ValueError),
    ],
)
async def test_failed_query_returns_client_to_pool(
    failure: BaseException, expected: type[BaseException]
) -> None:
    driver = Driver()
    pool = GatewayPool(driver.open, 1)
    await pool.select("SELECT 1")
    driver.drivers[0].failure = failure
    with pytest.raises(expected):
        await pool.select("SELECT broken")
    driver.drivers[0].failure = None
    assert await pool.select("SELECT 2") == [(0, "SELECT 2")]
    assert pool.opened == 1


async def test_refused_connection_frees_the_slot() -> None:
    driver = Driver()
    driver.refusals = 1
    pool = GatewayPool(driver.open, 1)
    with pytest.raises(RepositoryUnavailableError):
        await pool.select("SELECT 1")
    assert await pool.select("SELECT 1") == [(0, "SELECT 1")]
    assert pool.opened == 1


async def test_cancelled_caller_keeps_client_busy_until_query_ends() -> None:
    driver = Driver()
    pool = GatewayPool(driver.open, 1)
    await pool.select("SELECT 0")
    gate = threading.Event()
    driver.drivers[0].gate = gate
    first = asyncio.create_task(pool.select("SELECT slow"))
    await asyncio.sleep(0.05)
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    second = asyncio.create_task(pool.select("SELECT next"))
    await asyncio.sleep(0.05)
    assert not second.done()
    gate.set()
    assert await second == [(0, "SELECT next")]
    assert driver.activity.peak == 1


async def test_failure_after_cancellation_is_consumed() -> None:
    driver = Driver()
    pool = GatewayPool(driver.open, 1)
    await pool.select("SELECT 0")
    driver.drivers[0].failure = OSError("reset")
    task = asyncio.create_task(pool.select("SELECT slow"))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    driver.drivers[0].failure = None
    assert await pool.select("SELECT 1") == [(0, "SELECT 1")]


async def test_closing_closes_every_client_and_reopens_on_demand() -> None:
    driver = Driver()
    pool = GatewayPool(driver.open, 3)
    await select_many(pool, 6)
    await pool.aclose()
    assert [item.closed for item in driver.drivers] == [True, True, True]
    assert pool.opened == 0
    assert await pool.select("SELECT 1") == [(3, "SELECT 1")]


async def test_closing_reports_failure_after_closing_the_rest() -> None:
    driver = Driver()
    pool = GatewayPool(driver.open, 2)
    await select_many(pool, 4)
    driver.drivers[0].close_failure = OSError("close")
    with pytest.raises(OSError, match="close"):
        await pool.aclose()
    assert driver.drivers[1].closed


def test_pool_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="0"):
        GatewayPool(Driver().open, 0)
