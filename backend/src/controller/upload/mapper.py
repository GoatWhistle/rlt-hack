from uuid import UUID

from src.controller.search.dto import SearchResponseDto
from src.controller.search.mapper import to_response
from src.controller.upload.dto import (
    CountsDto,
    IssueDto,
    LotDetailDto,
    LotResultDto,
    LotResultsDto,
    LotSummaryDto,
    UploadDetailDto,
    UploadSummaryDto,
)
from src.models.procurement import LOT_ID_MAX_LENGTH, LOT_ID_PATTERN, RowIssue
from src.models.search_result import SearchResult
from src.models.upload import LotDetail, LotProgress, UploadDetail, UploadResults, UploadSummary
from src.service.errors import LotNotFoundError, UploadNotFoundError


def parse_upload_id(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError as error:
        raise UploadNotFoundError from error


def parse_lot_id(upload_id: UUID, raw: str) -> str:
    if len(raw) > LOT_ID_MAX_LENGTH or not LOT_ID_PATTERN.fullmatch(raw):
        raise LotNotFoundError(upload_id)
    return raw


def summary_dto(summary: UploadSummary) -> UploadSummaryDto:
    upload, counts = summary.upload, summary.counts
    return UploadSummaryDto(
        id=upload.upload_id,
        file_name=upload.file_name,
        created_at=upload.created_at,
        total=upload.total,
        processed=summary.processed,
        counts=CountsDto(
            ready=counts.ready,
            needs_check=counts.needs_check,
            no_candidates=counts.no_candidates,
            failed=counts.failed,
        ),
        rejected=upload.rejected,
    )


def lot_dto(progress: LotProgress) -> LotSummaryDto:
    lot = progress.lot
    price = lot.start_price
    return LotSummaryDto(
        id=lot.lot_id,
        title=lot.title,
        subject=lot.subject or None,
        customer_inn=lot.customer_inn or None,
        publish_date=None if lot.publish_date is None else lot.publish_date.isoformat(),
        start_price=None if price is None else float(price),
        status=progress.status,
        products=progress.products,
        candidates=progress.candidates,
        search_id=progress.search_id,
    )


def issue_dto(issue: RowIssue) -> IssueDto:
    return IssueDto(row=issue.row, code=issue.code, value=issue.value or None)


def detail_dto(detail: UploadDetail) -> UploadDetailDto:
    return UploadDetailDto(
        **summary_dto(detail.summary).model_dump(),
        lots=[lot_dto(progress) for progress in detail.lots],
        issues=[issue_dto(issue) for issue in detail.summary.upload.issues],
    )


def search_dto(search: SearchResult | None) -> SearchResponseDto | None:
    return None if search is None else to_response(search)


def lot_result_dto(progress: LotProgress, search: SearchResult | None) -> LotResultDto:
    return LotResultDto(lot=lot_dto(progress), search=search_dto(search))


def lot_detail_dto(detail: LotDetail) -> LotDetailDto:
    return LotDetailDto(
        lot=lot_dto(detail.progress),
        search=search_dto(detail.search),
        upload=summary_dto(detail.summary),
    )


def results_dto(results: UploadResults) -> LotResultsDto:
    return LotResultsDto(
        results=[lot_result_dto(entry.progress, entry.search) for entry in results.lots]
    )
