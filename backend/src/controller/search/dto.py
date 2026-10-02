from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, StringConstraints

from src.controller.http.schema import CamelModel, UtcDateTime
from src.models.enums import (
    Availability,
    CandidateStatus,
    CheckReason,
    CompanyRole,
    EvidenceKind,
    HighlightCode,
    ItemOrigin,
    ItemType,
    Locale,
    MatchBasis,
    PurchaseOutcome,
    VerificationStatus,
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


class SearchRequestDto(CamelModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str
    limit: int | None = None
    filters: FiltersDto = Field(default_factory=FiltersDto)


class QueryDto(CamelModel):
    text: str
    locale: Locale
    limit: int
    filters: FiltersDto


class QuantityDto(CamelModel):
    value: str
    unit: str


class ItemDto(CamelModel):
    id: str
    name: str
    okpd2: str
    item_type: ItemType
    origin: ItemOrigin
    quantity: QuantityDto | None


class SourceDto(CamelModel):
    kind: EvidenceKind
    title: str
    url: str
    checked_at: UtcDateTime


class AttributeDto(CamelModel):
    name: str
    value: str


class OfferDto(CamelModel):
    id: UUID
    name: str
    price: str | None
    currency: str
    unit: str
    availability: Availability
    brand: str = ""
    article: str = ""
    okpd2: str = ""
    attributes: list[AttributeDto] = Field(default_factory=list)
    image_url: str | None = None
    seller: VerificationStatus = VerificationStatus.UNVERIFIED
    source: SourceDto | None


class MatchDto(CamelModel):
    item_id: str
    basis: MatchBasis
    offer_id: UUID | None
    source: SourceDto | None


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


class PipelineDto(CamelModel):
    version: str
    channels: list[str]
    as_of: UtcDateTime


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
    offers: dict[UUID, OfferDto] = Field(default_factory=dict)


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
