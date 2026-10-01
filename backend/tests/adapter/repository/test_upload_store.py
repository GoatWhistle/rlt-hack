from dataclasses import replace

import pytest

from src.adapter.repository.clickhouse.upload_store.store import LOT_BATCH, ClickHouseUploadStore
from src.models.enums import CheckReason, LotStatus
from src.models.lot_result import LotResult
from src.models.upload import LotProgress
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.fakes.domain import MOMENT, make_candidate, uid
from tests.fakes.uploads import UPLOAD_ID, make_issue, make_lot, make_lot_result, make_upload

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb

LOTS = (
    make_lot("1"),
    replace(make_lot("2"), subject="", publish_date=None, start_price=None, customer_inn=""),
    make_lot("3"),
)


async def created(gateway: ChdbGateway) -> ClickHouseUploadStore:
    store = ClickHouseUploadStore(gateway)
    await store.create(make_upload(total=3, issues=(make_issue(),)), LOTS)
    return store


async def test_upload_and_lots_are_stored_and_listed(gateway: ChdbGateway) -> None:
    store = await created(gateway)
    detail = await store.detail(UPLOAD_ID)
    assert detail is not None
    assert detail.summary.upload == make_upload(total=3, issues=(make_issue(),))
    assert [progress.lot for progress in detail.lots] == list(LOTS)
    assert {progress.status for progress in detail.lots} == {LotStatus.QUEUED}
    assert [summary.upload.upload_id for summary in await store.recent(5)] == [UPLOAD_ID]
    assert await store.recent(0) == ()
    assert await store.detail(uid("missing")) is None
    assert await store.summary(uid("missing")) is None


async def test_results_update_progress_and_read_back(gateway: ChdbGateway) -> None:
    store = await created(gateway)
    checked = make_candidate(reasons=(CheckReason.INN_MISSING,))
    first = make_lot_result("1", candidates=(checked,))
    await store.save_result(UPLOAD_ID, first)
    await store.save_result(UPLOAD_ID, LotResult.failure("3", MOMENT))
    summary = await store.summary(UPLOAD_ID)
    assert summary is not None
    assert (summary.processed, summary.counts.needs_check, summary.counts.failed) == (2, 1, 1)
    lot = await store.lot(UPLOAD_ID, "1")
    assert lot is not None
    assert lot.result == first
    assert lot.progress == LotProgress(LOTS[0], LotStatus.NEEDS_CHECK, 1, 1)
    queued = await store.lot(UPLOAD_ID, "2")
    assert queued is not None
    assert queued.result is None
    assert await store.lot(UPLOAD_ID, "missing") is None
    assert await store.lot(uid("missing"), "1") is None
    results = await store.results(UPLOAD_ID, ["1", "2", "3"])
    assert [entry.result.lot_id for entry in results] == ["1", "3"]
    assert [lot.lot.lot_id for lot in await store.pending()] == ["2"]


async def test_latest_result_wins_and_many_lot_ids_are_batched(gateway: ChdbGateway) -> None:
    store = await created(gateway)
    await store.save_result(UPLOAD_ID, LotResult.failure("1", MOMENT))
    later = replace(make_lot_result("1"), processed_at=MOMENT.replace(hour=13))
    await store.save_result(UPLOAD_ID, later)
    wanted = ["1", *(f"x{number}" for number in range(LOT_BATCH + 5))]
    results = await store.results(UPLOAD_ID, wanted)
    assert [entry.result for entry in results] == [later]
