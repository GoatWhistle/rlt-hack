"""Публикует только полностью прочитанный и записанный каталог СТЕ."""

import hashlib
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
        digest = hashlib.sha256()
        async for page in self._provider.pages():
            expected = page.total
            await self._storage.stage(run_id, page.items)
            for item in page.items:
                digest.update(item.external_id.encode())
                digest.update(b"\0")
                digest.update(item.content_hash.encode())
                digest.update(b"\n")
            count += len(page.items)
            pages += 1
        if expected is None or count == 0 or count != expected:
            raise ValueError("неполный обход каталога СТЕ")
        verified = hashlib.sha256()
        verified_count = 0
        async for page in self._provider.pages():
            if page.total != expected:
                raise ValueError("счётчик СТЕ изменился при повторной сверке")
            for item in page.items:
                verified.update(item.external_id.encode())
                verified.update(b"\0")
                verified.update(item.content_hash.encode())
                verified.update(b"\n")
            verified_count += len(page.items)
        if verified_count != count or verified.digest() != digest.digest():
            raise ValueError("каталог СТЕ изменился между двумя полными обходами")
        await self._storage.publish(run_id, self._provider.source_id, count)
        return ProductSyncResult(run_id, count, pages)
