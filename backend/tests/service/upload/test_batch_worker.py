from decimal import Decimal

import pytest

from src.controller.uploads.csv_file import decode_notices
from src.controller.uploads.item_file import read_positions
from src.models.operations.upload import Notice, Upload
from src.models.search.supplier_search import SupplierCandidate
from src.service.search.supplier import SupplierSearch
from src.service.upload.worker import UploadService
from tests.service.search.test_batch_notices import RecordingEncoder, RecordingIndex, notices
from tests.service.upload.test_worker import OWNER, MemoryUploads


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
    upload = await service.create(OWNER, "notices.csv + items.csv", inputs)
    assert len(upload.lots) == 38
    assert sum(len(lot.notice.positions) for lot in upload.lots) == 670
    assert len(upload.lots[0].notice.positions) == 200
    assert [len(batch) for batch in encoder.calls] == [16, 16, 6]
    assert len(repository.saved) == 1
    persisted = await repository.get(OWNER, upload.upload_id)
    assert persisted == upload
    assert upload.lots[-1].notice.start_price == Decimal(38)
    assert upload.lots[-1].notice.customer_inn == "7801234564"


async def test_second_embedding_batch_failure_does_not_save_partial_upload() -> None:
    encoder = RecordingEncoder()
    encoder.fail_call = 2
    index = RecordingIndex()
    repository = MemoryUploads()
    service = UploadService(SupplierSearch(index, encoder), repository)
    with pytest.raises(RuntimeError, match="embedding unavailable"):
        await service.create(OWNER, "both.csv", notices(38))
    assert repository.saved == {}
    assert len(index.calls) == 16
    encoder.fail_call = None
    upload = await service.create(OWNER, "retry.csv", notices(38))
    assert len(upload.lots) == 38
    assert len(repository.saved) == 1


async def test_failed_refresh_keeps_previously_saved_results() -> None:
    encoder = RecordingEncoder()
    repository = MemoryUploads()
    service = UploadService(SupplierSearch(RecordingIndex(), encoder), repository)
    upload = await service.create(OWNER, "both.csv", notices(38))
    stale = Upload(
        upload.upload_id, upload.owner, upload.filename, upload.created_at, upload.lots, "old"
    )
    await repository.save(stale)
    encoder.fail_call = len(encoder.calls) + 2
    with pytest.raises(RuntimeError, match="embedding unavailable"):
        await service.get(OWNER, upload.upload_id)
    assert await repository.get(OWNER, upload.upload_id) == stale


class WrongCountSearch:
    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
        raise AssertionError("the batch interface must be used")

    async def search_notices(
        self, inputs: list[Notice], limit: int = 10
    ) -> list[list[SupplierCandidate]]:
        return [[]]


async def test_batch_response_count_mismatch_is_not_saved() -> None:
    repository = MemoryUploads()
    with pytest.raises(ValueError, match="shorter"):
        await UploadService(WrongCountSearch(), repository).create(OWNER, "a.csv", notices(2))
    assert repository.saved == {}
