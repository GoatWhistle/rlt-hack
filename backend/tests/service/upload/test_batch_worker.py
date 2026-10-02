from decimal import Decimal

from src.controller.uploads.csv_file import decode_notices
from src.controller.uploads.item_file import read_positions
from src.models.operations.upload import Notice, Upload
from src.models.search.supplier_search import SupplierCandidate
from src.service.search.supplier import SupplierSearch
from src.service.upload.worker import UploadService
from tests.service.search.test_batch_notices import RecordingEncoder, RecordingIndex, notices
from tests.service.upload.test_worker import OWNER, MemoryUploads


async def processed(service: UploadService, repository: MemoryUploads, upload_id: str) -> Upload:
    await service.drain()
    stored = await repository.get(OWNER, upload_id)
    assert stored is not None
    return stored


async def test_two_synthetic_csv_files_keep_all_38_lots_and_670_positions() -> None:
    notice_rows = ["lot_id;procedure_name;customer_inn;start_price"]
    item_rows = ["lot_id;product_name;okpd2_code"]
    for index in range(38):
        notice_rows.append(f"L{index};Purchase {index};7801234564;{index + 1}")
        count = 200 if index == 0 else (13 if index <= 26 else 12)
        item_rows.extend(f"L{index};p{item};17.12.14.110" for item in range(count))
    inputs = await read_positions(
        decode_notices("\n".join(notice_rows).encode()), "\n".join(item_rows).encode()
    )
    encoder = RecordingEncoder()
    supplier_index = RecordingIndex()
    repository = MemoryUploads()
    service = UploadService(SupplierSearch(supplier_index, encoder), repository)
    created = await service.create(OWNER, "notices.csv + items.csv", inputs)
    upload = await processed(service, repository, created.upload_id)
    assert len(upload.lots) == 38
    assert all(lot.processed and not lot.failed for lot in upload.lots)
    assert sum(len(lot.notice.positions) for lot in upload.lots) == 670
    assert len(upload.lots[0].notice.positions) == 200
    assert [len(batch) for batch in encoder.calls] == [16, 16, 6]
    assert len(repository.saved) == 1
    assert len(repository.history) == 4
    assert upload.ranking_version == "synthetic-snapshot/region-v1/okpd2-v1"
    assert upload.lots[-1].notice.start_price == Decimal(38)
    assert upload.lots[-1].notice.customer_inn == "7801234564"


async def test_second_embedding_batch_failure_marks_only_its_lots_failed() -> None:
    encoder = RecordingEncoder()
    encoder.fail_call = 2
    index = RecordingIndex()
    repository = MemoryUploads()
    service = UploadService(SupplierSearch(index, encoder), repository, retry_delays=())
    created = await service.create(OWNER, "both.csv", notices(38))
    upload = await processed(service, repository, created.upload_id)
    failed = [lot.failed for lot in upload.lots]
    assert failed == [False] * 16 + [True] * 16 + [False] * 6
    assert all(lot.processed for lot in upload.lots)
    assert all(not lot.candidates for lot in upload.lots[16:32])
    assert len(index.calls) == 22


async def test_failed_refresh_keeps_previously_saved_results() -> None:
    encoder = RecordingEncoder()
    repository = MemoryUploads()
    service = UploadService(SupplierSearch(RecordingIndex(), encoder), repository, retry_delays=())
    created = await service.create(OWNER, "both.csv", notices(38))
    upload = await processed(service, repository, created.upload_id)
    stale = Upload(
        upload.upload_id, upload.owner, upload.filename, upload.created_at, upload.lots, "old"
    )
    await repository.save(stale)
    encoder.fail_call = len(encoder.calls) + 2
    assert await service.get(OWNER, upload.upload_id) == stale
    assert await processed(service, repository, upload.upload_id) == stale


async def test_refresh_runs_in_background_and_saves_once_at_the_end() -> None:
    encoder = RecordingEncoder()
    repository = MemoryUploads()
    service = UploadService(SupplierSearch(RecordingIndex(), encoder), repository)
    created = await service.create(OWNER, "both.csv", notices(38))
    upload = await processed(service, repository, created.upload_id)
    stale = Upload(
        upload.upload_id, upload.owner, upload.filename, upload.created_at, upload.lots, "old"
    )
    await repository.save(stale)
    saves = len(repository.history)
    calls = len(encoder.calls)
    first = await service.get(OWNER, upload.upload_id)
    second = await service.get(OWNER, upload.upload_id)
    assert first == stale
    assert second == stale
    refreshed = await processed(service, repository, upload.upload_id)
    assert len(encoder.calls) - calls == 3
    assert len(repository.history) == saves + 1
    assert refreshed.ranking_version == upload.ranking_version
    assert all(lot.processed and not lot.failed for lot in refreshed.lots)


class WrongCountSearch:
    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
        raise AssertionError("the batch interface must be used")

    async def search_notices(
        self, inputs: list[Notice], limit: int = 10
    ) -> list[list[SupplierCandidate]]:
        return [[]]


async def test_batch_response_count_mismatch_marks_lots_failed() -> None:
    repository = MemoryUploads()
    service = UploadService(WrongCountSearch(), repository, retry_delays=())
    created = await service.create(OWNER, "a.csv", notices(2))
    upload = await processed(service, repository, created.upload_id)
    assert [(lot.processed, lot.failed) for lot in upload.lots] == [(True, True), (True, True)]
