import asyncio
import logging
from dataclasses import replace

import pytest

from src.models.enums import LotStatus
from src.models.upload import PendingLot
from src.service.procurement_upload.runner import LotRunner
from src.service.procurement_upload.settings import UploadSettings
from tests.fakes.ports import FixedClock
from tests.fakes.upload_ports import FakeProcessor, MemoryUploadStore
from tests.fakes.uploads import UPLOAD_ID, make_lot, make_upload
from tests.fakes.waiting import eventually

FAST = UploadSettings(retry_delay_seconds=0, resume_delay_seconds=0, concurrency=2)


def pending(*lot_ids: str) -> list[PendingLot]:
    return [PendingLot(UPLOAD_ID, make_lot(lot_id)) for lot_id in lot_ids]


async def stored(store: MemoryUploadStore, *lot_ids: str) -> MemoryUploadStore:
    await store.create(make_upload(total=len(lot_ids)), [make_lot(lot_id) for lot_id in lot_ids])
    return store


async def finish(runner: LotRunner, store: MemoryUploadStore, expected: int) -> None:
    async def saved() -> bool:
        return len(store.saved) >= expected

    await eventually(saved)
    await runner.drain()


async def test_submitted_lots_are_processed_and_saved() -> None:
    store = MemoryUploadStore()
    processor = FakeProcessor()
    runner = LotRunner(processor, store, FixedClock(), FAST)
    runner.submit(pending("1", "2", "3"))
    runner.submit(pending("1"))
    await runner.start()
    await runner.start()
    states = [runner.running]
    await finish(runner, store, 3)
    await runner.stop()
    states.append(runner.running)
    assert states == [True, False]
    assert sorted(processor.calls) == ["1", "2", "3"]
    assert {result.status for result in store.saved.values()} == {LotStatus.NO_CANDIDATES}


async def test_failures_are_retried_and_then_recorded() -> None:
    store = MemoryUploadStore(failing_saves=1)
    processor = FakeProcessor(failures={"1": 1, "2": 5})
    runner = LotRunner(processor, store, FixedClock(), FAST)
    await runner.start()
    runner.submit(pending("1", "2"))
    await finish(runner, store, 2)
    await runner.stop()
    assert processor.calls.count("1") == 2
    assert processor.calls.count("2") == FAST.attempts
    assert store.saved[(UPLOAD_ID, "1")].status == LotStatus.NO_CANDIDATES
    assert store.saved[(UPLOAD_ID, "2")].status == LotStatus.FAILED


async def test_unfinished_lots_resume_after_restart() -> None:
    store = await stored(MemoryUploadStore(failing_pending=1), "1", "2")
    first = FakeProcessor(gate=asyncio.Event())
    runner = LotRunner(first, store, FixedClock(), FAST)
    await runner.start()

    async def both_started() -> bool:
        return len(first.calls) == 2

    await eventually(both_started)
    await runner.stop()
    assert store.saved == {}
    second = FakeProcessor()
    restarted = LotRunner(second, store, FixedClock(), FAST)
    await restarted.start()
    await finish(restarted, store, 2)
    await restarted.stop()
    assert sorted(second.calls) == ["1", "2"]


async def test_lot_is_saved_after_store_recovers(caplog: pytest.LogCaptureFixture) -> None:
    store = await stored(MemoryUploadStore(failing_saves=FAST.attempts), "1")
    processor = FakeProcessor()
    runner = LotRunner(processor, store, FixedClock(), replace(FAST, resume_interval_seconds=0.01))
    with caplog.at_level(logging.ERROR):
        await runner.start()
        await finish(runner, store, 1)
        await runner.stop()
    assert store.saved[(UPLOAD_ID, "1")].status == LotStatus.NO_CANDIDATES
    assert processor.calls == ["1", "1"]
    assert "lot result was not saved and will be resumed" in caplog.text


async def test_resume_skips_lots_already_in_work() -> None:
    store = await stored(MemoryUploadStore(), "1")
    processor = FakeProcessor(gate=asyncio.Event())
    runner = LotRunner(processor, store, FixedClock(), replace(FAST, resume_interval_seconds=0.01))
    await runner.start()
    await asyncio.sleep(0.1)
    assert processor.calls == ["1"]
    assert processor.gate is not None
    processor.gate.set()
    await finish(runner, store, 1)
    await runner.stop()


@pytest.mark.parametrize(
    ("error", "calls"),
    [(ValueError("bad lot"), 1), (KeyError("column"), 1), (TimeoutError(), 2)],
)
async def test_deterministic_error_is_not_retried(error: Exception, calls: int) -> None:
    store = MemoryUploadStore()
    processor = FakeProcessor(errors={"1": error})
    runner = LotRunner(processor, store, FixedClock(), replace(FAST, attempts=5))
    await runner.start()
    runner.submit(pending("1"))
    await finish(runner, store, 1)
    await runner.stop()
    assert processor.calls == ["1"] * calls
    assert store.saved[(UPLOAD_ID, "1")].status == LotStatus.FAILED


def test_resume_interval_must_be_positive() -> None:
    with pytest.raises(ValueError, match="resume interval"):
        replace(FAST, resume_interval_seconds=0)
