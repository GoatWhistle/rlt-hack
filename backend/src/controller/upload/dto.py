from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, StringConstraints

from src.controller.http.schema import CamelModel, UtcDateTime
from src.controller.search.dto import (
    ContactsDto,
    HighlightDto,
    PipelineDto,
    SourceDto,
    WarningDto,
)
from src.models.enums import (
    CandidateStatus,
    CheckReason,
    CompanyRole,
    IssueCode,
    LotStatus,
    MatchBasis,
    PurchaseOutcome,
)
from src.models.procurement import LOT_ID_MAX_LENGTH

MAX_SELECTED_LOTS = 5000

ProductOrigin = Literal["notice", "inferred", "user"]


class CountsDto(CamelModel):
    ready: int
    needs_check: int
    no_candidates: int
    failed: int


class UploadSummaryDto(CamelModel):
    id: UUID
    file_name: str
    created_at: UtcDateTime
    total: int
    processed: int
    counts: CountsDto
    rejected: int


class UploadListDto(CamelModel):
    uploads: list[UploadSummaryDto]


class LotSummaryDto(CamelModel):
    id: str
    title: str
    subject: str | None
    customer_inn: str | None
    publish_date: str | None
    start_price: float | None
    status: LotStatus
    products: int
    candidates: int


class IssueDto(CamelModel):
    row: int
    code: IssueCode
    value: str | None


class UploadDetailDto(UploadSummaryDto):
    lots: list[LotSummaryDto]
    issues: list[IssueDto]


class ProductDto(CamelModel):
    id: str
    name: str
    okpd2: str
    origin: ProductOrigin
    origin_note: None = None


class ProductMatchDto(CamelModel):
    product_id: str
    basis: MatchBasis
    source: SourceDto | None


class CompanyPurchaseDto(CamelModel):
    lot_id: str
    title: str
    year: int | None
    outcome: PurchaseOutcome
    source: SourceDto | None


class CompanyDto(CamelModel):
    id: UUID
    name: str
    inn: str
    role: CompanyRole
    role_source: SourceDto | None
    contacts: ContactsDto
    status: CandidateStatus
    check_reasons: list[CheckReason]
    highlights: list[HighlightDto]
    matches: list[ProductMatchDto]
    similar_purchases: int
    wins: int
    purchases: list[CompanyPurchaseDto]


class RecommendationDto(CamelModel):
    file_name: str
    request_title: str
    lot_label: str
    products: list[ProductDto]
    companies: list[CompanyDto]
    warnings: list[WarningDto]
    pipeline: PipelineDto | None


class LotResultDto(CamelModel):
    lot: LotSummaryDto
    recommendation: RecommendationDto | None


class LotDetailDto(LotResultDto):
    upload: UploadSummaryDto


class LotResultsDto(CamelModel):
    results: list[LotResultDto]


class ResultsRequestDto(CamelModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    lot_ids: list[Annotated[str, StringConstraints(max_length=LOT_ID_MAX_LENGTH)]] = Field(
        max_length=MAX_SELECTED_LOTS
    )
