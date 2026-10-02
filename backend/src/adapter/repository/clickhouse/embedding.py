"""Хранилище векторов позиций.

Свежесть вектора определяется хешем всех полей, попадающих в его текст, а не
хешем смысловых полей предложения: в текст входят ещё название, регион и адрес
компании, и их правка обязана пересчитать вектор. Хеш считается здесь, в SQL,
одним выражением на чтении и на поиске — тогда он не расходится с набором
полей, которые читает тот же запрос.
"""

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.rows import to_uuid
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.models.embedding import EmbeddingDocument, OfferSearchHit
from src.models.search import SearchFilters

# Порядок совпадает с порядком полей EmbeddingDocument после content_hash.
DOCUMENT_COLUMNS = (
    "o.name",
    "o.normalized_name",
    "o.brand",
    "o.article",
    "toString(o.item_type)",
    "o.unit",
    "o.source_category",
    "o.okpd2_code",
    "o.rubric_name",
    "toString(o.supplier_role)",
    "ifNull(s.name, '')",
    "ifNull(s.region, '')",
    "ifNull(s.contacts['address'], '')",
    "o.description",
    "o.attributes",
)

# Характеристики хешируются отсортированными: порядок ключей в Map зависит от
# адаптера, а смысл позиции от него не зависит.
_SORTED_ATTRIBUTES = "toString(arraySort(arrayZip(mapKeys(o.attributes), mapValues(o.attributes))))"

# Хеш предложения входит в хеш документа отдельным слагаемым, хотя в текст не
# попадает: его считает адаптер, и смена правил разбора обязана пересчитать
# вектор, даже если прочитанные поля на вид остались теми же.
_HASH_INPUTS = ("o.content_hash", *DOCUMENT_COLUMNS[:-1], _SORTED_ATTRIBUTES)
DOCUMENT_HASH = "toString(cityHash64(" + ", ".join(_HASH_INPUTS) + "))"

_JOIN_SUPPLIERS = "LEFT JOIN {db}.suppliers_current AS s ON s.supplier_id = o.supplier_id "


class ClickHouseEmbeddingRepository:
    def __init__(
        self, gateway: SqlGateway, versions: VersionSequencer, database: str = "supplier_search"
    ) -> None:
        self._gateway = gateway
        self._versions = versions
        self._db = database

    async def pending(self, model_key: str, dimensions: int, limit: int) -> list[EmbeddingDocument]:
        rows = await self._gateway.select(
            f"SELECT o.offer_id, {DOCUMENT_HASH}, {', '.join(DOCUMENT_COLUMNS)} "
            f"FROM {self._db}.offers_current AS o "
            + _JOIN_SUPPLIERS.format(db=self._db)
            + f"LEFT JOIN (SELECT * FROM {self._db}.embeddings_current "
            "WHERE entity_type = 'offer' AND model_key = {model:String} "
            "AND dimensions = {dimensions:UInt16}) AS e ON e.entity_id = o.offer_id "
            "WHERE o.availability != 'unavailable' AND o.content_hash != '' "
            f"AND o.name != '' AND ifNull(e.content_hash, '') != {DOCUMENT_HASH} "
            "ORDER BY o.offer_id LIMIT {limit:UInt32}",
            {"model": model_key, "dimensions": dimensions, "limit": limit},
        )
        return [EmbeddingDocument(to_uuid(row[0]), *row[1:]) for row in rows]

    async def save(
        self, documents: list[EmbeddingDocument], vectors: list[list[float]], model_key: str
    ) -> None:
        await self._gateway.insert(
            f"{self._db}.embeddings",
            (
                "entity_type",
                "entity_id",
                "model_key",
                "dimensions",
                "embedding",
                "content_hash",
                "version",
                "is_deleted",
            ),
            [
                (
                    "offer",
                    document.offer_id,
                    model_key,
                    len(vector),
                    vector,
                    document.content_hash,
                    self._versions.next(),
                    0,
                )
                for document, vector in zip(documents, vectors, strict=True)
            ],
        )

    async def search(self, vector: list[float], model_key: str, limit: int) -> list[OfferSearchHit]:
        return await self.search_filtered(vector, model_key, limit, SearchFilters())

    async def search_filtered(
        self, vector: list[float], model_key: str, limit: int, filters: SearchFilters
    ) -> list[OfferSearchHit]:
        rows = await self._gateway.select(
            f"SELECT o.offer_id, o.name, o.url, o.supplier_id, "
            "1 - cosineDistance(e.embedding, {vector:Array(Float32)}) AS similarity "
            f"FROM {self._db}.embeddings_current AS e "
            f"INNER JOIN {self._db}.offers_current AS o ON e.entity_id = o.offer_id "
            + _JOIN_SUPPLIERS.format(db=self._db)
            + "WHERE e.entity_type = 'offer' AND e.model_key = {model:String} "
            f"AND e.dimensions = {{dimensions:UInt16}} AND e.content_hash = {DOCUMENT_HASH} "
            "AND o.availability != 'unavailable' "
            "AND (empty({regions:Array(String)}) OR s.region IN {regions:Array(String)}) "
            "AND ({item_type:String} = '' OR toString(o.item_type) = {item_type:String}) "
            "ORDER BY similarity DESC, o.offer_id LIMIT 3 BY o.supplier_id LIMIT {limit:UInt32}",
            {
                "vector": vector,
                "model": model_key,
                "dimensions": len(vector),
                "limit": limit,
                "regions": list(filters.regions),
                "item_type": str(filters.item_type or ""),
            },
        )
        return [
            OfferSearchHit(
                to_uuid(row[0]), row[1], row[2], to_uuid(row[3]) if row[3] else None, float(row[4])
            )
            for row in rows
        ]
