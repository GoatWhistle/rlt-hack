from uuid import UUID

from src.controller.search.mapper import (
    contacts_dto,
    highlight_dto,
    pipeline_dto,
    source_dto,
    warning_dto,
)
from src.controller.upload.dto import (
    CompanyDto,
    CompanyPurchaseDto,
    CountsDto,
    IssueDto,
    LotDetailDto,
    LotResultDto,
    LotResultsDto,
    LotSummaryDto,
    ProductDto,
    ProductMatchDto,
    ProductOrigin,
    RecommendationDto,
    UploadDetailDto,
    UploadSummaryDto,
)
from src.models.candidate import ProductMatch, SupplierCandidate
from src.models.enums import ItemOrigin
from src.models.lot_result import LotResult
from src.models.procurement import LOT_ID_MAX_LENGTH, LOT_ID_PATTERN, RowIssue
from src.models.purchase import PurchaseRecord
from src.models.query_item import QueryItem
from src.models.upload import (
    LotDetail,
    LotProgress,
    UploadDetail,
    UploadResults,
    UploadSummary,
)
from src.service.errors import LotNotFoundError, UploadNotFoundError

PRODUCT_ORIGINS: dict[ItemOrigin, ProductOrigin] = {
    ItemOrigin.TEXT: "notice",
    ItemOrigin.INFERRED: "inferred",
    ItemOrigin.USER: "user",
}


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
    )


def issue_dto(issue: RowIssue) -> IssueDto:
    return IssueDto(row=issue.row, code=issue.code, value=issue.value or None)


def detail_dto(detail: UploadDetail) -> UploadDetailDto:
    return UploadDetailDto(
        **summary_dto(detail.summary).model_dump(),
        lots=[lot_dto(progress) for progress in detail.lots],
        issues=[issue_dto(issue) for issue in detail.summary.upload.issues],
    )


def product_dto(item: QueryItem) -> ProductDto:
    return ProductDto(
        id=item.item_id, name=item.name, okpd2=item.okpd2, origin=PRODUCT_ORIGINS[item.origin]
    )


def match_dto(match: ProductMatch) -> ProductMatchDto:
    return ProductMatchDto(
        product_id=match.item_id, basis=match.basis, source=source_dto(match.evidence)
    )


def purchase_dto(record: PurchaseRecord) -> CompanyPurchaseDto:
    return CompanyPurchaseDto(
        lot_id=record.lot_id, title=record.title, year=None, outcome=record.outcome, source=None
    )


def company_dto(candidate: SupplierCandidate) -> CompanyDto:
    supplier = candidate.supplier
    return CompanyDto(
        id=supplier.supplier_id,
        name=supplier.name,
        inn=supplier.inn or "",
        role=candidate.role,
        role_source=source_dto(candidate.role_evidence),
        contacts=contacts_dto(supplier),
        status=candidate.status,
        check_reasons=list(candidate.check_reasons),
        highlights=[highlight_dto(highlight) for highlight in candidate.highlights],
        matches=[match_dto(match) for match in candidate.matches],
        similar_purchases=candidate.history.similar,
        wins=candidate.history.wins,
        purchases=[purchase_dto(record) for record in candidate.history.records],
    )


def recommendation_dto(
    file_name: str, progress: LotProgress, result: LotResult | None
) -> RecommendationDto | None:
    if result is None or result.failed:
        return None
    return RecommendationDto(
        file_name=file_name,
        request_title=progress.lot.title,
        lot_label=progress.lot.lot_id,
        products=[product_dto(item) for item in result.items],
        companies=[company_dto(candidate) for candidate in result.candidates],
        warnings=[warning_dto(warning) for warning in result.warnings],
        pipeline=None if result.pipeline is None else pipeline_dto(result.pipeline),
    )


def lot_result_dto(file_name: str, progress: LotProgress, result: LotResult | None) -> LotResultDto:
    return LotResultDto(
        lot=lot_dto(progress), recommendation=recommendation_dto(file_name, progress, result)
    )


def lot_detail_dto(detail: LotDetail) -> LotDetailDto:
    file_name = detail.summary.upload.file_name
    return LotDetailDto(
        lot=lot_dto(detail.progress),
        recommendation=recommendation_dto(file_name, detail.progress, detail.result),
        upload=summary_dto(detail.summary),
    )


def results_dto(results: UploadResults) -> LotResultsDto:
    file_name = results.summary.upload.file_name
    return LotResultsDto(
        results=[lot_result_dto(file_name, entry.progress, entry.result) for entry in results.lots]
    )
