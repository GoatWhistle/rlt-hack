"""Срез аналитики: согласованные показатели каталога на один момент."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.models.analytics.filters import AnalyticsFilters, FreshnessPolicy
from src.models.analytics.measure import CountRow, Ratio
from src.models.enums import FetchStatus, SourceType


@dataclass(frozen=True, slots=True)
class CategoryRow:
    code: str
    parent: str
    offers: int
    companies: int
    verified_sellers: int
    fresh: int
    priced: int
    searchable: int
    system_assigned: int
    source_reported: int


@dataclass(frozen=True, slots=True)
class SourceRow:
    source_id: UUID
    name: str
    provider_name: str
    source_type: SourceType
    offers: int
    companies: int
    fresh: int
    unknown_age: int
    last_seen_at: datetime | None
    last_success_at: datetime | None
    last_attempt_at: datetime | None
    last_attempt_status: FetchStatus | None
    runs: int
    failed_runs: int


@dataclass(frozen=True, slots=True)
class RunRow:
    run_id: UUID
    source_id: UUID
    source_name: str
    provider_name: str
    started_at: datetime
    finished_at: datetime
    status: FetchStatus
    suppliers_extracted: int
    offers_extracted: int
    error_message: str


@dataclass(frozen=True, slots=True)
class ProblemRow:
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


@dataclass(frozen=True, slots=True)
class AnalyticsSlice:
    snapshot_id: UUID
    as_of: datetime
    computed_at: datetime
    definitions_version: str
    filters: AnalyticsFilters
    policy: FreshnessPolicy
    offers: int
    companies: int
    composition: tuple[CountRow, ...]
    fresh: Ratio
    searchable: Ratio
    priced: Ratio
    runs_success: Ratio
    runs_partial: int
    age: tuple[CountRow, ...]
    availability: tuple[CountRow, ...]
    origins: tuple[CountRow, ...]
    categories: tuple[CategoryRow, ...]
    sources: tuple[SourceRow, ...]
    runs: tuple[RunRow, ...]
    problems: tuple[ProblemRow, ...]
