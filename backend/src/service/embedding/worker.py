import asyncio
import logging
import math
import time

from src.models.embedding import EmbeddingDocument, OfferSearchHit
from src.service.embedding.protocols import EmbeddingRepository, TextEmbedder
from src.service.errors import ServiceError

logger = logging.getLogger(__name__)


# Тип позиции и роль компании хранятся кодами: в тексте вектора они заменяются
# словом, потому что запросы приходят словами, а не кодами схемы.
ITEM_TYPES = {"goods": "товар", "work": "работа", "service": "услуга"}
ROLES = {
    "manufacturer": "производитель",
    "distributor": "дистрибьютор",
    "reseller": "перепродавец",
    "service_provider": "исполнитель услуг",
}
MAX_DOCUMENT_LENGTH = 12000


def document_text(document: EmbeddingDocument) -> str:
    """Текст для энкодера: всё, что отличает позицию, включая место поставщика.

    Поля подписаны, потому что без подписи модель не отличает регион от бренда.
    Цена и наличие в текст не входят: они меняются часто и предмет не уточняют,
    поэтому их изменение не должно пересчитывать вектор.
    """
    attributes = "; ".join(f"{key}: {value}" for key, value in sorted(document.attributes.items()))
    location = ", ".join(dict.fromkeys(filter(None, (document.region, document.address))))
    parts = (
        document.name,
        _labelled("Предмет", document.normalized_name)
        if document.normalized_name != document.name
        else "",
        _labelled("Тип", ITEM_TYPES.get(document.item_type, document.item_type)),
        _labelled("Бренд", document.brand),
        _labelled("Артикул", document.article),
        _labelled("Характеристики", attributes),
        _labelled("Единица", document.unit),
        _labelled("Раздел каталога", document.source_category),
        _labelled("ОКПД2", document.okpd2_code),
        _labelled("Рубрика", document.rubric_name),
        _labelled("Поставщик", document.supplier_name),
        _labelled("Роль", ROLES.get(document.supplier_role, "")),
        _labelled("Местоположение", location),
        document.description,
    )
    return "\n".join(filter(None, parts))[:MAX_DOCUMENT_LENGTH]


def _labelled(label: str, value: str) -> str:
    value = " ".join(value.split())
    return f"{label}: {value}" if value else ""


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
        if interval <= 0 or not 1 <= batch_size <= 32:
            raise ServiceError("неверный интервал или размер батча")
        waiting_since = None
        while True:
            try:
                documents = await self._repository.pending(
                    self._encoder.model_key, self._encoder.dimensions, batch_size
                )
                now = time.monotonic()
                if not documents:
                    waiting_since = None
                else:
                    if waiting_since is None:
                        waiting_since = now
                    if len(documents) >= batch_size or now - waiting_since >= interval:
                        vectors = await self._encoder.encode(
                            [document_text(item) for item in documents]
                        )
                        self._validate(vectors, len(documents))
                        await self._repository.save(documents, vectors, self._encoder.model_key)
                        logger.info("Indexed batch of %d offers", len(documents))
                        waiting_since = None
                        continue
            except Exception:
                logger.exception("Embedding batch failed; will retry")
                await asyncio.sleep(interval)
            await asyncio.sleep(min(1.0, interval))

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
