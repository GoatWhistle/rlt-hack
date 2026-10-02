from uuid import UUID

from src.controller.http.schema import CamelModel, UtcDateTime
from src.models.enums import FetchStatus, SourceType


class RatioDto(CamelModel):
    numerator: int
    denominator: int
    unknown: int
    share: float | None


class CountDto(CamelModel):
    key: str
    count: int


class AnalyticsFiltersDto(CamelModel):
    source_id: UUID | None
    source_type: SourceType | None
    region: str | None


class PolicyDto(CamelModel):
    offer_days: int
    registry_days: int
    period_days: int
    version: str


class MetaDto(CamelModel):
    snapshot_id: UUID
    as_of: UtcDateTime
    computed_at: UtcDateTime
    definitions_version: str
    delay_seconds: int
    warnings: list[str]
    filters: AnalyticsFiltersDto
    policy: PolicyDto


class AttentionDto(CamelModel):
    code: str
    source_id: UUID | None
    count: int
    total: int


class CategoryDto(CamelModel):
    code: str
    name: str
    parent: str
    offers: int
    share: RatioDto
    companies: int
    verified_sellers: RatioDto
    fresh: RatioDto
    priced: RatioDto
    searchable: RatioDto
    system_assigned: int
    source_reported: int


class AnalyticsSourceDto(CamelModel):
    source_id: UUID
    name: str
    provider_name: str
    source_type: SourceType
    state: str
    offers: int
    companies: int
    fresh: RatioDto
    last_seen_at: UtcDateTime | None
    last_success_at: UtcDateTime | None
    last_attempt_at: UtcDateTime | None
    last_attempt_status: FetchStatus | None
    runs: int
    failed_runs: int


class RunDto(CamelModel):
    run_id: UUID
    source_id: UUID
    source_name: str
    provider_name: str
    started_at: UtcDateTime
    finished_at: UtcDateTime
    duration_seconds: int
    status: FetchStatus
    suppliers_extracted: int
    offers_extracted: int
    error_message: str


class ProblemDto(CamelModel):
    source_id: UUID
    name: str
    offers: int
    no_supplier: int
    unverified_seller: int
    no_category: int
    no_price: int
    no_attributes: int
    stale: int
    unknown_age: int


class OverviewDto(CamelModel):
    meta: MetaDto
    offers: int
    companies: int
    composition: list[CountDto]
    fresh: RatioDto
    searchable: RatioDto
    runs_success: RatioDto
    runs_partial: int
    attention: list[AttentionDto]
    categories: list[CategoryDto]
    sources: list[AnalyticsSourceDto]
    runs: list[RunDto]


class CategoriesDto(CamelModel):
    meta: MetaDto
    offers: int
    items: list[CategoryDto]
    origins: list[CountDto]


class QualityDto(CamelModel):
    meta: MetaDto
    offers: int
    fresh: RatioDto
    priced: RatioDto
    age: list[CountDto]
    availability: list[CountDto]
    problems: list[ProblemDto]


class AnalyticsSourcesDto(CamelModel):
    meta: MetaDto
    items: list[AnalyticsSourceDto]


class RunsDto(CamelModel):
    meta: MetaDto
    success: RatioDto
    partial: int
    items: list[RunDto]


class RecordDto(CamelModel):
    offer_id: UUID
    name: str
    source_id: UUID
    source_name: str
    supplier_id: UUID | None
    supplier_name: str
    okpd2_code: str
    price: float | None
    currency: str
    url: str
    last_seen_at: UtcDateTime
    updated_at: UtcDateTime


class RecordsDto(CamelModel):
    as_of: UtcDateTime
    total: int
    changed_after: int
    items: list[RecordDto]
