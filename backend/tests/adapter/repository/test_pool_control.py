import asyncio
import logging
import re
import threading
import time

import pytest

from src.adapter.repository.clickhouse.pool.control import KILL_QUERY, ControlChannel
from src.adapter.repository.clickhouse.pool.gateway import GatewayPool
from src.adapter.repository.clickhouse.probe.probe import ClickHouseProbe
from tests.adapter.repository.pool_fakes import Driver, KillSwitch

QUERY_ID = re.compile(r"[0-9a-f]{32}")


async def blocked_pool(
    driver: Driver, control: KillSwitch | None
) -> tuple[GatewayPool, threading.Event]:
    pool = GatewayPool(driver.open, 1, control)
    await pool.select("SELECT 0")
    gate = threading.Event()
    driver.drivers[0].gate = gate
    return pool, gate


async def cancel_slow_select(pool: GatewayPool) -> None:
    task = asyncio.create_task(pool.select("SELECT slow"))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_every_statement_gets_its_own_query_id() -> None:
    driver = Driver()
    pool = GatewayPool(driver.open, 1)
    await pool.select("SELECT 1")
    await pool.command("OPTIMIZE")
    await pool.insert("t", ("a",), [(1,)])
    ids = driver.drivers[0].query_ids
    assert len(set(ids)) == 3
    assert all(QUERY_ID.fullmatch(query_id) for query_id in ids)


async def test_cancelled_lease_kills_running_query() -> None:
    driver = Driver()
    switch = KillSwitch()
    pool, gate = await blocked_pool(driver, switch)
    switch.gates.append(gate)
    await cancel_slow_select(pool)
    started = time.perf_counter()
    assert await pool.select("SELECT next") == [(0, "SELECT next")]
    assert time.perf_counter() - started < 1
    assert switch.killed == [driver.drivers[0].query_ids[1]]
    await pool.aclose()


async def test_finished_queries_are_not_killed() -> None:
    driver = Driver()
    switch = KillSwitch()
    pool = GatewayPool(driver.open, 2, switch)
    await asyncio.gather(pool.select("SELECT 1"), pool.select("SELECT 2"))
    assert switch.killed == []


async def test_failed_kill_is_logged_and_the_slot_returns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    driver = Driver()
    switch = KillSwitch(failure=RuntimeError("no rights"))
    pool, gate = await blocked_pool(driver, switch)
    with caplog.at_level(logging.WARNING):
        await cancel_slow_select(pool)
        await asyncio.sleep(0.02)
    assert "cancelled query was not killed" in caplog.text
    gate.set()
    assert await pool.select("SELECT next") == [(0, "SELECT next")]


async def test_control_channel_reuses_one_client_and_reopens_after_close() -> None:
    driver = Driver()
    control = ControlChannel(driver.open)
    await control.kill("abc")
    assert await control.select("SELECT 1") == [(0, "SELECT 1")]
    await control.insert("t", ("a",), [(1,)])
    assert len(driver.drivers) == 1
    assert driver.drivers[0].statements == [KILL_QUERY, "SELECT 1", "t"]
    await control.aclose()
    await control.aclose()
    assert driver.drivers[0].closed
    await control.command("SELECT 2")
    assert len(driver.drivers) == 2


async def test_probe_does_not_wait_for_busy_pool() -> None:
    driver = Driver()
    pool, gate = await blocked_pool(driver, None)
    busy = asyncio.create_task(pool.select("SELECT slow"))
    await asyncio.sleep(0.05)
    probe = ClickHouseProbe(ControlChannel(Driver().open))
    await asyncio.wait_for(probe.check(), 0.5)
    gate.set()
    await busy
