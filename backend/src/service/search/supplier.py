import asyncio
import math

from src.models.search_context import SearchContext
from src.models.supplier_search import SupplierCandidate
from src.models.upload import Notice
from src.service.errors import ServiceError
from src.service.search.protocols import (
    ContextualSupplierIndex,
    IndexVersion,
    QueryEncoder,
    SupplierIndex,
)


class SupplierSearch:
    def __init__(self, index: SupplierIndex, encoder: QueryEncoder) -> None:
        self._index = index
        self._encoder = encoder
        self._lock = asyncio.Lock()

    @property
    def version(self) -> str:
        return self._index.version if isinstance(self._index, IndexVersion) else ""

    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]:
        return await self._index.enrich(candidates)

    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
        return await self._search(text, limit, None)

    async def search_notice(self, notice: Notice, limit: int = 10) -> list[SupplierCandidate]:
        text = "\n".join(filter(None, (notice.title, notice.subject)))
        return await self._search(
            text, limit, SearchContext(notice.customer_inn, notice.start_price)
        )

    async def _search(
        self, text: str, limit: int, context: SearchContext | None
    ) -> list[SupplierCandidate]:
        text = text.strip()
        if not text or len(text) > 4000 or not 1 <= limit <= 100:
            raise ServiceError("неверный запрос или лимит")
        async with self._lock:
            vectors = await self._encoder.encode(
                [f"Instruct: {self._index.instruction}\nQuery: {text}"], query=False
            )
            if (
                len(vectors) != 1
                or len(vectors[0]) != self._index.dimensions
                or not all(math.isfinite(value) for value in vectors[0])
                or not any(vectors[0])
            ):
                raise ServiceError("несовместимый вектор запроса")
            if context is not None and isinstance(self._index, ContextualSupplierIndex):
                return await self._index.search_context(text, vectors[0], limit, context)
            return await self._index.search(text, vectors[0], limit)
