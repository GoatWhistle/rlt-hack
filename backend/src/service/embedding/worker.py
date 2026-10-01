import asyncio
import logging
import math

from src.models.embedding import EmbeddingDocument, OfferSearchHit
from src.service.embedding.protocols import EmbeddingRepository, TextEmbedder
from src.service.errors import ServiceError

logger = logging.getLogger(__name__)


def document_text(document: EmbeddingDocument) -> str:
    attributes = "; ".join(f"{key}: {value}" for key, value in sorted(document.attributes.items()))
    return "\n".join(
        filter(
            None,
            (
                document.name,
                document.brand,
                document.article,
                attributes,
                document.description,
            ),
        )
    )[:12000]


class EmbeddingWorker:
    def __init__(self, repository: EmbeddingRepository, encoder: TextEmbedder) -> None:
        self._repository = repository
        self._encoder = encoder

    async def run_once(self, batch_size: int = 1, max_batches: int = 1) -> int:
        if not 1 <= batch_size <= 32 or max_batches < 1:
            raise ServiceError("неверный размер обработки эмбеддингов")
        indexed = 0
        for _ in range(max_batches):
            documents = await self._repository.pending(
                self._encoder.model_key, self._encoder.dimensions, batch_size
            )
            if not documents:
                break
            vectors = await self._encoder.encode([document_text(item) for item in documents])
            self._validate(vectors, len(documents))
            await self._repository.save(documents, vectors, self._encoder.model_key)
            indexed += len(documents)
            logger.info("Indexed %s offers; model=%s", indexed, self._encoder.model_key)
        return indexed

    async def run_forever(self, batch_size: int, interval: float) -> None:
        if interval <= 0:
            raise ServiceError("интервал должен быть положительным")
        while True:
            try:
                count = await self.run_once(batch_size)
            except Exception:
                logger.exception("Embedding batch failed; will retry")
                count = 0
            if not count:
                await asyncio.sleep(interval)

    async def search(self, text: str, limit: int = 5) -> list[OfferSearchHit]:
        if not text.strip() or len(text) > 12000 or not 1 <= limit <= 100:
            raise ServiceError("неверный поисковый запрос или лимит")
        vectors = await self._encoder.encode([text], query=True)
        self._validate(vectors, 1)
        return await self._repository.search(vectors[0], self._encoder.model_key, limit)

    def _validate(self, vectors: list[list[float]], count: int) -> None:
        if len(vectors) != count:
            raise ServiceError("энкодер вернул неверное число векторов")
        for vector in vectors:
            if (
                len(vector) != self._encoder.dimensions
                or not all(math.isfinite(value) for value in vector)
                or not any(vector)
            ):
                raise ServiceError("энкодер вернул некорректный вектор")
