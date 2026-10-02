from typing import Protocol
from uuid import UUID

from src.models.search import SearchQuery
from src.models.search_result import SearchResult, SearchSummary
from src.models.supplier_search import SupplierCandidate


class SearchEngine(Protocol):
    @property
    def version(self) -> str: ...

    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]: ...


class SupplierSearching(Protocol):
    async def search(self, query: SearchQuery) -> SearchResult: ...

    async def get(self, search_id: UUID) -> SearchResult: ...

    async def recent(self, limit: int) -> tuple[SearchSummary, ...]: ...
