"""Пакетная запись СТЕ и атомарная публикация завершённого обхода."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.models.product import Product

COLUMNS = (
    "run_id",
    "product_id",
    "source_id",
    "external_id",
    "url",
    "name",
    "description",
    "item_type",
    "category_id",
    "category_path",
    "classifier_codes",
    "attributes",
    "unit",
    "brand",
    "manufacturer",
    "country",
    "image_urls",
    "raw_json",
    "content_hash",
)


class ClickHouseMoscowProductRepository:
    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._database = database

    async def stage(self, run_id: UUID, products: Sequence[Product]) -> None:
        await self._gateway.insert(
            f"{self._database}.moscow_products",
            COLUMNS,
            [
                (
                    run_id,
                    item.product_id,
                    item.source_id,
                    item.external_id,
                    item.url,
                    item.name,
                    item.description,
                    str(item.item_type),
                    item.category_id,
                    list(item.category_path),
                    item.classifier_codes,
                    item.attributes,
                    item.unit,
                    item.brand,
                    item.manufacturer,
                    item.country,
                    list(item.image_urls),
                    item.raw_json,
                    item.content_hash,
                )
                for item in products
            ],
        )

    async def publish(self, run_id: UUID, source_id: UUID, expected: int) -> None:
        rows = await self._gateway.select(
            f"SELECT count(), uniqExact(product_id) FROM {self._database}.moscow_products "
            "WHERE run_id = {run_id:UUID} AND source_id = {source_id:UUID}",
            {"run_id": str(run_id), "source_id": str(source_id)},
        )
        if not rows or tuple(map(int, rows[0])) != (expected, expected):
            raise ValueError("число записанных СТЕ не совпадает с полным обходом")
        await self._gateway.insert(
            f"{self._database}.moscow_product_publications",
            ("run_id", "source_id", "product_count", "completed_at"),
            [(run_id, source_id, expected, datetime.now(UTC))],
        )
