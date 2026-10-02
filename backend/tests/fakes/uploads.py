from datetime import date
from decimal import Decimal

from src.models.enums import IssueCode
from src.models.lot_result import LotResult
from src.models.procurement import NoticeFile, ProcurementLot, RowIssue
from src.models.search_result import SearchResult
from src.models.upload import (
    LotDetail,
    LotProgress,
    ProcessedLot,
    StatusCounts,
    Upload,
    UploadDetail,
    UploadSummary,
)
from tests.fakes.domain import MOMENT, make_candidate, make_result, uid

UPLOAD_ID = uid("upload")
OWNER = "a" * 32
OTHER_OWNER = "b" * 32


def make_lot(
    lot_id: str = "4257576", title: str = "Поставка крупы", row: int = 2
) -> ProcurementLot:
    return ProcurementLot(
        lot_id=lot_id,
        title=title,
        row=row,
        subject="Крупа гречневая ядрица 500 кг",
        customer_inn="7807022750",
        publish_date=date(2024, 1, 18),
        start_price=Decimal("2835.54"),
    )


def make_notices(*lots: ProcurementLot, issues: tuple[RowIssue, ...] = ()) -> NoticeFile:
    return NoticeFile(lots=lots or (make_lot(),), issues=issues)


def make_upload(total: int = 1, issues: tuple[RowIssue, ...] = ()) -> Upload:
    return Upload(
        upload_id=UPLOAD_ID,
        file_name="notices.csv",
        created_at=MOMENT,
        total=total,
        issues=issues,
        owner=OWNER,
    )


def make_issue(row: int = 5, code: IssueCode = IssueCode.BAD_PRICE, value: str = "abc") -> RowIssue:
    return RowIssue(row, code, value)


def make_search() -> SearchResult:
    return make_result(make_candidate())


def make_lot_result(lot_id: str = "4257576", search: SearchResult | None = None) -> LotResult:
    return LotResult.of_search(lot_id, MOMENT, search or make_search())


def make_summary(upload: Upload | None = None, counts: StatusCounts | None = None) -> UploadSummary:
    return UploadSummary(upload or make_upload(), counts or StatusCounts())


def make_detail(result: LotResult | None = None) -> UploadDetail:
    lot = make_lot()
    progress = LotProgress.of(lot, result)
    counts = StatusCounts.tally([progress.status] if result is not None else [])
    return UploadDetail(
        summary=make_summary(make_upload(issues=(make_issue(),)), counts), lots=(progress,)
    )


def make_lot_detail(result: LotResult | None = None) -> LotDetail:
    detail = make_detail(result)
    search = make_search() if result is not None and result.search_id is not None else None
    return LotDetail(detail.summary, detail.lots[0], result, search)


def make_processed(result: LotResult | None = None) -> ProcessedLot:
    outcome = result or make_lot_result()
    search = make_search() if outcome.search_id is not None else None
    return ProcessedLot(LotProgress.of(make_lot(outcome.lot_id), outcome), outcome, search)
