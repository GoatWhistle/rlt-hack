from typing import Protocol
from uuid import UUID

from src.models.operations.upload import Notice
from src.models.ranking.embedding import OfferSearchHit
from src.models.search.search import SearchQuery
from src.models.search.search_result import SearchResult, SearchSummary
from src.models.search.supplier_search import SupplierCandidate


class SearchEngine(Protocol):
    async def search_notice(self, notice: Notice, limit: int = 10) -> list[SupplierCandidate]: ...

    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]: ...


class SupplierSearching(Protocol):
    async def search(self, query: SearchQuery) -> SearchResult: ...

    async def get(self, search_id: UUID) -> SearchResult: ...

    async def recent(self, limit: int) -> tuple[SearchSummary, ...]: ...


class CatalogSearching(Protocol):
    async def search(
        self, text: str, limit: int, regions: list[str], item_type: str | None
    ) -> list[OfferSearchHit]: ...
