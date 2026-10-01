from uuid import UUID

import pytest

from src.models.enums import LotStatus
from src.models.errors import NoValidLotsError, TooManyNoticeRowsError
from src.models.procurement import NoticeFile
from src.service.errors import LotNotFoundError, UploadNotFoundError, UploadQueueFullError
from src.service.procurement_upload.runner import LotRunner
from src.service.procurement_upload.service import ProcurementUploadService
from src.service.procurement_upload.settings import UploadSettings
from tests.fakes.domain import uid
from tests.fakes.ports import FixedClock, SequentialIds
from tests.fakes.upload_ports import FakeProcessor, FakeReader, MemoryUploadStore
from tests.fakes.uploads import make_issue, make_lot, make_notices
from tests.fakes.waiting import eventually

SETTINGS = UploadSettings(retry_delay_seconds=0, resume_delay_seconds=0, max_rows=10)


def build(
    reader: FakeReader, store: MemoryUploadStore, processor: FakeProcessor | None = None
) -> ProcurementUploadService:
    runner = LotRunner(processor or FakeProcessor(failures={"3": 9}), store, FixedClock(), SETTINGS)
    return ProcurementUploadService(
        reader=reader,
        store=store,
        runner=runner,
        clock=FixedClock(),
        ids=SequentialIds(),
        settings=SETTINGS,
    )


async def processed(service: ProcurementUploadService, upload_id: UUID, total: int) -> None:
    async def done() -> bool:
        return (await service.get(upload_id)).summary.processed >= total

    await eventually(done)


async def test_upload_is_split_into_lots_and_processed_in_background() -> None:
    notices = make_notices(make_lot("1"), make_lot("2"), make_lot("3"), issues=(make_issue(),))
    reader = FakeReader(notices)
    store = MemoryUploadStore()
    service = build(reader, store)
    await service.start()
    summary = await service.upload("dir/notices.csv", b"payload")
    assert reader.calls == [(b"payload", 10)]
    assert (summary.upload.file_name, summary.upload.total, summary.processed) == (
        "notices.csv",
        3,
        0,
    )
    assert summary.upload.rejected == 1
    await processed(service, summary.upload.upload_id, 3)
    detail = await service.get(summary.upload.upload_id)
    assert [lot.status for lot in detail.lots] == [
        LotStatus.NO_CANDIDATES,
        LotStatus.NO_CANDIDATES,
        LotStatus.FAILED,
    ]
    assert (detail.summary.counts.no_candidates, detail.summary.counts.failed) == (2, 1)
    assert [entry.upload.upload_id for entry in await service.recent(5)] == [
        summary.upload.upload_id
    ]
    await service.stop()


async def test_lots_and_results_are_read_back() -> None:
    store = MemoryUploadStore()
    service = build(FakeReader(make_notices(make_lot("1"), make_lot("3"))), store)
    await service.start()
    upload_id = (await service.upload("n.csv", b"")).upload.upload_id
    await processed(service, upload_id, 2)
    summary = await service.summary(upload_id)
    assert (summary.processed, summary.upload.total) == (2, 2)
    lot = await service.lot(upload_id, "1")
    assert lot.result is not None
    assert lot.progress.status == LotStatus.NO_CANDIDATES
    results = await service.results(upload_id, ["3", "1", "1", "missing"])
    assert [entry.result.lot_id for entry in results.lots] == ["1"]
    assert (await service.results(upload_id, [])).lots == ()
    await service.stop()


async def test_missing_uploads_and_lots_are_reported() -> None:
    store = MemoryUploadStore()
    service = build(FakeReader(make_notices()), store)
    with pytest.raises(UploadNotFoundError):
        await service.get(uid("nothing"))
    with pytest.raises(UploadNotFoundError):
        await service.summary(uid("nothing"))
    with pytest.raises(UploadNotFoundError):
        await service.lot(uid("nothing"), "1")
    with pytest.raises(UploadNotFoundError):
        await service.results(uid("nothing"), ["1"])
    upload_id = (await service.upload("n.csv", b"")).upload.upload_id
    with pytest.raises(LotNotFoundError):
        await service.lot(upload_id, "missing")


async def test_files_without_valid_lots_are_rejected() -> None:
    store = MemoryUploadStore()
    with pytest.raises(NoValidLotsError):
        await build(FakeReader(NoticeFile(lots=())), store).upload("n.csv", b"")
    reader = FakeReader(make_notices(), error=TooManyNoticeRowsError(10))
    with pytest.raises(TooManyNoticeRowsError):
        await build(reader, store).upload("n.csv", b"")
    assert store.uploads == {}


async def test_rejects_upload_when_backlog_is_full() -> None:
    settings = UploadSettings(retry_delay_seconds=0, max_rows=2, max_backlog=3)
    store = MemoryUploadStore()
    reader = FakeReader(make_notices(make_lot("1"), make_lot("2")))
    runner = LotRunner(FakeProcessor(), store, FixedClock(), settings)
    service = ProcurementUploadService(
        reader=reader,
        store=store,
        runner=runner,
        clock=FixedClock(),
        ids=SequentialIds(),
        settings=settings,
    )
    await service.upload("first.csv", b"1")
    assert runner.backlog == 2
    with pytest.raises(UploadQueueFullError) as raised:
        await service.upload("second.csv", b"2")
    assert raised.value.limit == 3
    assert len(store.uploads) == 1


def test_backlog_must_hold_a_full_file() -> None:
    with pytest.raises(ValueError, match="backlog"):
        UploadSettings(max_rows=10, max_backlog=9)
