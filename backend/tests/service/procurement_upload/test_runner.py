import asyncio

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
