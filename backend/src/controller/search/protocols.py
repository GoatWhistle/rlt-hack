from typing import Protocol
from uuid import UUID

from src.models.search import SearchQuery
from src.models.search_result import SearchResult, SearchSummary


class SupplierSearching(Protocol):
    async def search(self, query: SearchQuery) -> SearchResult: ...

    async def get(self, search_id: UUID) -> SearchResult: ...

    async def recent(self, limit: int) -> tuple[SearchSummary, ...]: ...
