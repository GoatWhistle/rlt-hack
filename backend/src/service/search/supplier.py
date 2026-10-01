import asyncio
import math

from src.models.supplier_search import SupplierCandidate
from src.service.errors import ServiceError
from src.service.search.protocols import QueryEncoder, SupplierIndex


class SupplierSearch:
    def __init__(self, index: SupplierIndex, encoder: QueryEncoder) -> None:
        self._index = index
        self._encoder = encoder
        self._lock = asyncio.Lock()

    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]:
        return await self._index.enrich(candidates)

    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
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
            return await self._index.search(text, vectors[0], limit)
