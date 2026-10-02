from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.models.analytics.filters import AnalyticsFilters, FreshnessPolicy
from src.models.analytics.records import RecordPage, RecordQuery
from src.models.analytics.slice import AnalyticsSlice


class SliceStore(Protocol):
    async def latest(self, scope_key: str) -> AnalyticsSlice | None: ...

    async def publish(self, snapshot: AnalyticsSlice) -> None: ...


class SliceBuilder(Protocol):
    async def build(
        self,
        snapshot_id: UUID,
        filters: AnalyticsFilters,
        policy: FreshnessPolicy,
        as_of: datetime,
        computed_at: datetime,
    ) -> AnalyticsSlice: ...


class RecordReader(Protocol):
    async def page(
        self,
        filters: AnalyticsFilters,
        query: RecordQuery,
        policy: FreshnessPolicy,
        as_of: datetime,
    ) -> RecordPage: ...


class CategoryNames(Protocol):
    def name_of(self, code: str) -> str: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
