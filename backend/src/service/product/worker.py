"""Публикует только полностью прочитанный и записанный каталог СТЕ."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.service.product.protocols import ProductProvider, ProductStorage


@dataclass(frozen=True, slots=True)
class ProductSyncResult:
    run_id: UUID
    product_count: int
    pages_fetched: int


class ProductSyncWorker:
    def __init__(self, provider: ProductProvider, storage: ProductStorage) -> None:
        self._provider = provider
        self._storage = storage

    async def run_once(self) -> ProductSyncResult:
        run_id = uuid4()
        count = 0
        pages = 0
        expected: int | None = None
        async for page in self._provider.pages():
            expected = page.total
            await self._storage.stage(run_id, page.items)
            count += len(page.items)
            pages += 1
        if expected is None or count != expected:
            raise ValueError("неполный обход каталога СТЕ")
        await self._storage.publish(run_id, self._provider.source_id, count)
        return ProductSyncResult(run_id, count, pages)
