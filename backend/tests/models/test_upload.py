from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from src.models.enums import CheckReason, IssueCode, ItemOrigin, LotStatus
from src.models.errors import (
    InvalidLotResultError,
    InvalidProcurementLotError,
    InvalidUploadError,
)
from src.models.lot_result import LotResult
from src.models.procurement import NoticeFile, ProcurementLot, RowIssue
from src.models.search import SearchText
from src.models.upload import (
    LotProgress,
    ProcessedLot,
    StatusCounts,
    Upload,
    UploadSummary,
    base_name,
)
from tests.fakes.domain import MOMENT, make_candidate, make_item, make_result, uid
from tests.fakes.uploads import make_issue, make_lot, make_lot_result, make_upload


def test_lot_normalizes_text_and_drops_a_subject_equal_to_the_title() -> None:
    lot = ProcurementLot(
        "L-1_a", "  Поставка   круп ", 3, subject="Поставка круп", customer_inn=" 78 "
    )
    assert (lot.title, lot.subject, lot.customer_inn) == ("Поставка круп", "", "78")
    assert lot.search_text == "Поставка круп"
    assert make_lot().search_text == "Крупа гречневая ядрица 500 кг"


def test_search_text_fits_the_search_limit() -> None:
    lot = ProcurementLot("1", "а" * (SearchText.MAX_LENGTH + 10), 2)
    assert len(lot.search_text) == SearchText.MAX_LENGTH


@pytest.mark.parametrize(
    "changes",
    [
        {"lot_id": "bad id"},
        {"lot_id": "x" * 65},
        {"title": "   "},
        {"row": 0},
        {"start_price": Decimal(-1)},
        {"start_price": Decimal("NaN")},
    ],
)
def test_invalid_lots_are_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(InvalidProcurementLotError):
        replace(make_lot(), **changes)


def test_issues_and_files_keep_their_invariants() -> None:
    with pytest.raises(InvalidUploadError):
        RowIssue(0, IssueCode.BAD_DATE)
    with pytest.raises(InvalidUploadError):
        NoticeFile(lots=(make_lot(), make_lot()))
    issues = (make_issue(5), make_issue(5, IssueCode.BAD_DATE), make_issue(7))
    assert NoticeFile(lots=(make_lot(),), issues=issues).rejected == 2


def test_upload_keeps_only_the_base_name() -> None:
    upload = Upload.of(
        uid("u"), "C:\\temp\\dir/notices  2024.csv", MOMENT, NoticeFile((make_lot(),))
    )
    assert (upload.file_name, upload.total, upload.rejected) == ("notices 2024.csv", 1, 0)
    assert base_name("a/b/") == ""


@pytest.mark.parametrize(
    "changes",
    [{"file_name": "dir/"}, {"total": 0}, {"created_at": datetime(2026, 1, 1)}],
)
def test_invalid_uploads_are_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(InvalidUploadError):
        replace(make_upload(), **changes)


def test_lot_status_follows_the_leading_candidate() -> None:
    assert make_lot_result().status == LotStatus.READY
    checked = make_candidate(reasons=(CheckReason.INN_MISSING,))
    assert make_lot_result(search=make_result(checked)).status == LotStatus.NEEDS_CHECK
    inferred = replace(make_item(), origin=ItemOrigin.INFERRED)
    assumed = make_result(make_candidate(), items=(inferred,))
    assert make_lot_result(search=assumed).status == LotStatus.NEEDS_CHECK
    assert make_lot_result(search=make_result()).status == LotStatus.NO_CANDIDATES
    assert LotResult.failure("1", MOMENT).status == LotStatus.FAILED
    assert LotResult.not_understood("1", MOMENT).status == LotStatus.NO_CANDIDATES


@pytest.mark.parametrize(
    "changes",
    [
        {"lot_id": ""},
        {"processed_at": datetime(2026, 1, 1)},
        {"status": LotStatus.FAILED},
        {"status": LotStatus.QUEUED},
        {"status": LotStatus.NO_CANDIDATES},
        {"search_id": None},
        {"products": -1},
    ],
)
def test_invalid_lot_results_are_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(InvalidLotResultError):
        replace(make_lot_result(), **changes)


def test_progress_counts_and_summary() -> None:
    lot = make_lot()
    assert LotProgress.of(lot, None) == LotProgress(lot)
    done = LotProgress.of(lot, make_lot_result())
    assert (done.status, done.products, done.candidates) == (LotStatus.READY, 1, 1)
    with pytest.raises(InvalidUploadError):
        LotProgress(lot, products=-1)
    counts = StatusCounts.tally(
        [LotStatus.READY, LotStatus.FAILED, LotStatus.NEEDS_CHECK, LotStatus.NO_CANDIDATES]
    )
    assert (counts.ready, counts.needs_check, counts.no_candidates, counts.failed) == (1, 1, 1, 1)
    assert counts.processed == 4
    with pytest.raises(InvalidUploadError):
        StatusCounts(ready=-1)
    summary = UploadSummary(make_upload(total=4), counts)
    assert (summary.processed, summary.finished) == (4, True)
    assert not UploadSummary(make_upload(total=5), counts).finished
    with pytest.raises(InvalidUploadError):
        UploadSummary(make_upload(total=3), counts)


def test_processed_lot_pairs_matching_ids() -> None:
    result = make_lot_result()
    ProcessedLot(LotProgress(make_lot()), result)
    with pytest.raises(InvalidUploadError):
        ProcessedLot(LotProgress(make_lot("other")), result)
