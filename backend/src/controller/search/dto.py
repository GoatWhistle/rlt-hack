from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, StringConstraints

from src.controller.http.schema import CamelModel, UtcDateTime
from src.models.enums import (
    Availability,
    CandidateOrigin,
    CandidateStatus,
    CheckReason,
    CompanyRole,
    EvidenceKind,
    HighlightCode,
    ItemOrigin,
    ItemType,
    LinkMethod,
    Locale,
    MatchBasis,
    Novelty,
    PurchaseOutcome,
    RequirementStatus,
    SearchOrigin,
    SourceType,
    WarningCode,
)

FilterItemType = Literal["goods", "work", "service"]
MAX_REGIONS = 100
REGION_MAX_LENGTH = 100


class FiltersDto(CamelModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    regions: list[Annotated[str, StringConstraints(max_length=REGION_MAX_LENGTH)]] = Field(
        default_factory=list, max_length=MAX_REGIONS
    )
    item_type: FilterItemType | None = None


class ContextDto(CamelModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    customer_inn: Annotated[str, StringConstraints(max_length=12)] | None = None
    start_price: Annotated[str, StringConstraints(max_length=32)] | None = None


class SearchRequestDto(CamelModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str
    limit: int | None = None
    filters: FiltersDto = Field(default_factory=FiltersDto)
    context: ContextDto = Field(default_factory=ContextDto)


class QueryDto(CamelModel):
    text: str
    locale: Locale
    limit: int
    filters: FiltersDto
    context: ContextDto
    origin: SearchOrigin


class QuantityDto(CamelModel):
    value: str
    unit: str


class RequirementDto(CamelModel):
    key: str
    value: str
    text: str


class ItemDto(CamelModel):
    id: str
    name: str
    okpd2: str
    item_type: ItemType
    origin: ItemOrigin
    quantity: QuantityDto | None
    requirements: list[RequirementDto]


class SourceDto(CamelModel):
    kind: EvidenceKind
    title: str
    url: str
    checked_at: UtcDateTime


class OfferSnapshotDto(CamelModel):
    id: UUID
    name: str
    url: str
    source_name: str
    source_type: SourceType
    observed_at: UtcDateTime
    link: LinkMethod
    brand: str | None
    article: str | None
    unit: str | None
    price: str | None
    currency: str | None
    availability: Availability


class CheckDto(CamelModel):
    key: str
    value: str
    text: str
    status: RequirementStatus
    found: str | None


class MatchDto(CamelModel):
    item_id: str
    basis: MatchBasis
    offer_id: UUID | None
    source: SourceDto | None
    offer: OfferSnapshotDto | None
    checks: list[CheckDto]


class PurchaseDto(CamelModel):
    lot_id: str
    title: str
    outcome: PurchaseOutcome
    item_ids: list[str]


class HistoryDto(CamelModel):
    similar_purchases: int
    wins: int
    records: list[PurchaseDto]


class HighlightDto(CamelModel):
    code: HighlightCode
    params: dict[str, int]


class ChannelRankDto(CamelModel):
    channel: str
    rank: int


class ScoreDto(CamelModel):
    total: float
    fusion: float
    coverage: float
    evidence: float
    history: float
    channels: list[ChannelRankDto]


class ContactsDto(CamelModel):
    site: str
    email: str
    phone: str


class CandidateDto(CamelModel):
    rank: int
    id: UUID
    name: str
    inn: str
    region: str
    role: CompanyRole
    role_source: SourceDto | None
    status: CandidateStatus
    check_reasons: list[CheckReason]
    matches: list[MatchDto]
    history: HistoryDto
    highlights: list[HighlightDto]
    score: ScoreDto
    contacts: ContactsDto
    origins: list[CandidateOrigin]
    novelty: Novelty


class PipelineDto(CamelModel):
    version: str
    channels: list[str]
    as_of: UtcDateTime
    inputs: list[str]
    novelty_set: str | None


class WarningDto(CamelModel):
    code: WarningCode
    subject: str


class SearchResponseDto(CamelModel):
    search_id: UUID
    query: QueryDto
    items: list[ItemDto]
    candidates: list[CandidateDto]
    pipeline: PipelineDto
    warnings: list[WarningDto]
    created_at: UtcDateTime


class SearchSummaryDto(CamelModel):
    search_id: UUID
    text: str
    locale: Locale
    items: int
    candidates: int
    recommended: int
    created_at: UtcDateTime


class RecentSearchesDto(CamelModel):
    searches: list[SearchSummaryDto]
