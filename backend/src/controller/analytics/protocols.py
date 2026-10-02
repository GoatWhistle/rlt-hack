from typing import Protocol

from src.models.analytics.filters import AnalyticsFilters
from src.models.analytics.records import RecordPage, RecordQuery
from src.models.analytics.view import AnalyticsView


class CatalogAnalytics(Protocol):
    async def view(self, filters: AnalyticsFilters) -> AnalyticsView: ...

    async def records(self, filters: AnalyticsFilters, query: RecordQuery) -> RecordPage: ...
