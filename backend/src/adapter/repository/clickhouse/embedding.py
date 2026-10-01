from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.rows import to_uuid
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.models.embedding import EmbeddingDocument, OfferSearchHit


class ClickHouseEmbeddingRepository:
    def __init__(
        self, gateway: SqlGateway, versions: VersionSequencer, database: str = "supplier_search"
    ) -> None:
        self._gateway = gateway
        self._versions = versions
        self._db = database

    async def pending(self, model_key: str, dimensions: int, limit: int) -> list[EmbeddingDocument]:
        rows = await self._gateway.select(
            f"SELECT o.offer_id, o.content_hash, o.name, o.brand, o.article, "
            f"o.description, o.attributes FROM {self._db}.offers_current AS o "
            f"LEFT JOIN (SELECT * FROM {self._db}.embeddings_current "
            "WHERE entity_type = 'offer' AND model_key = {model:String} "
            "AND dimensions = {dimensions:UInt16}) AS e ON e.entity_id = o.offer_id "
            "WHERE o.availability != 'unavailable' AND o.content_hash != '' "
            "AND o.name != '' AND ifNull(e.content_hash, '') != o.content_hash "
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
        rows = await self._gateway.select(
            f"SELECT o.offer_id, o.name, o.url, o.supplier_id, "
            "1 - cosineDistance(e.embedding, {vector:Array(Float32)}) AS similarity "
            f"FROM {self._db}.embeddings_current AS e "
            f"INNER JOIN {self._db}.offers_current AS o ON e.entity_id = o.offer_id "
            "WHERE e.entity_type = 'offer' AND e.model_key = {model:String} "
            "AND e.dimensions = {dimensions:UInt16} AND e.content_hash = o.content_hash "
            "AND o.availability != 'unavailable' "
            "ORDER BY similarity DESC, o.offer_id LIMIT {limit:UInt32}",
            {"vector": vector, "model": model_key, "dimensions": len(vector), "limit": limit},
        )
        return [
            OfferSearchHit(
                to_uuid(row[0]), row[1], row[2], to_uuid(row[3]) if row[3] else None, float(row[4])
            )
            for row in rows
        ]
