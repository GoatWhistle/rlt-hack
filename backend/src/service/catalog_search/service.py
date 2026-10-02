import asyncio
import math

from src.models.enums import ItemType
from src.models.ranking.embedding import OfferSearchHit
from src.models.search.search import SearchFilters
from src.service.catalog_search.protocols import CatalogIndex, QueryEncoder
from src.service.errors import ServiceError


class CatalogSearch:
    def __init__(self, index: CatalogIndex, encoder: QueryEncoder) -> None:
        self._index = index
        self._encoder = encoder
        self._slots = asyncio.Semaphore(2)

    async def search(
        self, text: str, limit: int, regions: list[str], item_type: str | None
    ) -> list[OfferSearchHit]:
        if not text.strip() or len(text) > 4000 or not 1 <= limit <= 100:
            raise ServiceError("invalid catalog query")
        filters = SearchFilters(tuple(regions), ItemType(item_type) if item_type else None)
        async with self._slots:
            vectors = await self._encoder.encode([text], query=True)
            if (
                len(vectors) != 1
                or len(vectors[0]) != self._encoder.dimensions
                or not all(math.isfinite(value) for value in vectors[0])
                or not any(vectors[0])
            ):
                raise ServiceError("invalid catalog query vector")
            return await self._index.search_filtered(
                vectors[0], self._encoder.model_key, limit, filters
            )
