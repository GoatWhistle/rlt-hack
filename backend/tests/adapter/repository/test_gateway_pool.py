import asyncio
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest
from clickhouse_connect.driver.exceptions import DatabaseError

from src.adapter.repository.clickhouse.gateway import ConnectGateway
from src.adapter.repository.clickhouse.pool.gateway import GatewayPool
from src.adapter.repository.errors import RepositoryError, RepositoryUnavailableError


@dataclass(slots=True)
class QueryResult:
    result_rows: list[list[Any]]


@dataclass(slots=True)
class Activity:
    delay: float = 0.02
    active: int = 0
    peak: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def enter(self) -> None:
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)

    def leave(self) -> None:
        with self.lock:
            self.active -= 1


class FakeDriver:
    def __init__(self, activity: Activity, number: int) -> None:
        self.activity = activity
        self.number = number
        self.closed = False
        self.close_failure: BaseException | None = None
        self.failure: BaseException | None = None
        self.gate: threading.Event | None = None
        self.statements: list[str] = []

    def query(self, statement: str, parameters: Mapping[str, Any]) -> QueryResult:
        self._work(statement)
        return QueryResult([[self.number, statement]])

    def command(self, statement: str, parameters: Mapping[str, Any]) -> None:
        self._work(statement)

    def insert(self, table: str, rows: Sequence[Sequence[Any]], column_names: list[str]) -> None:
        self._work(table)

    def close(self) -> None:
        if self.close_failure is not None:
            raise self.close_failure
        self.closed = True

    def _work(self, statement: str) -> None:
        self.activity.enter()
        try:
            if self.gate is not None:
                self.gate.wait(5)
            time.sleep(self.activity.delay)
            self.statements.append(statement)
            if self.failure is not None:
                raise self.failure
        finally:
            self.activity.leave()


class Driver:
    def __init__(self) -> None:
        self.activity = Activity()
        self.drivers: list[FakeDriver] = []
        self.refusals = 0

    async def open(self) -> ConnectGateway:
        await asyncio.sleep(0)
        if self.refusals:
            self.refusals -= 1
            raise RepositoryUnavailableError("refused")
        driver = FakeDriver(self.activity, len(self.drivers))
        self.drivers.append(driver)
        return ConnectGateway(driver)


async def select_many(pool: GatewayPool, count: int) -> list[list[tuple[Any, ...]]]:
    return await asyncio.gather(*(pool.select(f"SELECT {index}") for index in range(count)))


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
