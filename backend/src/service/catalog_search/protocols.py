from typing import Protocol

from src.models.embedding import OfferSearchHit
from src.models.search import SearchFilters


class QueryEncoder(Protocol):
    model_key: str
    dimensions: int

    async def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]: ...


class CatalogIndex(Protocol):
    async def search_filtered(
        self, vector: list[float], model_key: str, limit: int, filters: SearchFilters
    ) -> list[OfferSearchHit]: ...
