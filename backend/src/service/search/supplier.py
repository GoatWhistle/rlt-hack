import asyncio
import math
from dataclasses import replace

from src.models.operations.upload import Notice
from src.models.search.search_context import SearchContext
from src.models.search.supplier_search import SupplierCandidate
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
        if isinstance(self._index, IndexVersion):
            return self._index.version + "/region-v1/okpd2-v1"
        return ""

    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]:
        return await self._index.enrich(candidates)

    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
        return await self._search(text, limit, None)

    async def search_notice(self, notice: Notice, limit: int = 10) -> list[SupplierCandidate]:
        return (await self.search_notices([notice], limit))[0]

    async def search_notices(
        self, notices: list[Notice], limit: int = 10
    ) -> list[list[SupplierCandidate]]:
        texts = [notice.query_text.strip() for notice in notices]
        if not 1 <= limit <= 100 or any(not text or len(text) > 4000 for text in texts):
            raise ServiceError("неверный запрос или лимит")
        results = []
        async with self._lock:
            for start in range(0, len(notices), 16):
                batch = notices[start : start + 16]
                queries = texts[start : start + 16]
                vectors = await self._encoder.encode(
                    [f"Instruct: {self._index.instruction}\nQuery: {text}" for text in queries],
                    query=False,
                )
                await self._validate_vectors(vectors, len(batch))
                for notice, text, vector in zip(batch, queries, vectors, strict=True):
                    context = SearchContext(
                        notice.customer_inn,
                        notice.start_price,
                        notice.delivery_region,
                        tuple(sorted({item.okpd2 for item in notice.positions if item.okpd2})),
                    )
                    results.append(await self._rank(text, vector, limit, context))
        return results

    async def _validate_vectors(self, vectors: list[list[float]], count: int) -> None:
        if len(vectors) != count or any(
            len(vector) != self._index.dimensions
            or not all(math.isfinite(value) for value in vector)
            or not any(vector)
            for vector in vectors
        ):
            raise ServiceError("несовместимый вектор запроса")

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
            await self._validate_vectors(vectors, 1)
            return await self._rank(text, vectors[0], limit, context)

    async def _rank(
        self, text: str, vector: list[float], limit: int, context: SearchContext | None
    ) -> list[SupplierCandidate]:
        if context is not None and isinstance(self._index, ContextualSupplierIndex):
            candidates = await self._index.search_context(
                text, vector, 100 if context.delivery_region else limit, context
            )
            if context.delivery_region:
                candidates = [
                    replace(
                        candidate,
                        score=candidate.score + 0.1,
                        ranking_reasons=list(dict.fromkeys(["region", *candidate.ranking_reasons]))[
                            :3
                        ],
                    )
                    if candidate.registered_region == context.delivery_region
                    else candidate
                    for candidate in candidates
                ]
                candidates.sort(
                    key=lambda candidate: (
                        -candidate.matched_category_count,
                        -candidate.score,
                        candidate.inn,
                    )
                )
            return candidates[:limit]
        return await self._index.search(text, vector, limit)
