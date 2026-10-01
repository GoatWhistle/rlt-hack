"""Публикует только полностью прочитанный и записанный каталог СТЕ."""

import hashlib
import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from src.service.product.protocols import ProductProvider, ProductStorage

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProductSyncResult:
    run_id: UUID
    product_count: int
    pages_fetched: int
    names_changed: bool
    summary_only_count: int


class ProductSyncWorker:
    def __init__(self, provider: ProductProvider, storage: ProductStorage) -> None:
        self._provider = provider
        self._storage = storage

    async def run_once(self) -> ProductSyncResult:
        run_id = uuid4()
        count = 0
        pages = 0
        expected: int | None = None
        identities = hashlib.sha256()
        first_names = hashlib.sha256()
        async for page in self._provider.listing_pages():
            expected = page.total
            for item in page.items:
                identities.update(item.external_id.encode())
                identities.update(b"\n")
                first_names.update(item.name.strip().encode())
                first_names.update(b"\n")
            count += len(page.items)
            pages += 1
        if expected is None or count == 0 or count != expected:
            raise ValueError("неполный обход каталога СТЕ")
        verified_ids = hashlib.sha256()
        current_names = hashlib.sha256()
        verified_count = 0
        summary_only_count = 0
        async for page in self._provider.pages():
            pages += 1
            if page.total != expected:
                raise ValueError("счётчик СТЕ изменился при повторной сверке")
            for item in page.items:
                verified_ids.update(item.external_id.encode())
                verified_ids.update(b"\n")
                current_names.update(item.name.strip().encode())
                current_names.update(b"\n")
                summary_only_count += item.detail_status == "summary_only"
            await self._storage.stage(run_id, page.items)
            verified_count += len(page.items)
        if verified_count != count or verified_ids.digest() != identities.digest():
            raise ValueError("состав СТЕ изменился между двумя полными обходами")
        await self._storage.publish(run_id, self._provider.source_id, count)
        changed = current_names.digest() != first_names.digest()
        return ProductSyncResult(run_id, count, pages, changed, summary_only_count)


@dataclass(frozen=True, slots=True)
class ProductCollectionResult:
    run_id: UUID
    staged_count: int
    pages_fetched: int
    source_total: int
    last_id: int | None


class ProductCollectionWorker:
    def __init__(self, provider: ProductProvider, storage: ProductStorage) -> None:
        self._provider = provider
        self._storage = storage

    async def run_pages(self, run_id: UUID, max_pages: int) -> ProductCollectionResult:
        count, previous_id = await self._storage.collection_progress(
            run_id, self._provider.source_id
        )
        pages = 0
        total = 0
        async for page in self._provider.collect_pages(count, previous_id, max_pages):
            await self._storage.stage(run_id, page.items)
            count += len(page.items)
            previous_id = int(page.items[-1].external_id)
            total = page.total
            pages += 1
            logger.info(
                "СТЕ: run=%s staged=%s source_total=%s last_id=%s",
                run_id,
                count,
                total,
                previous_id,
            )
        return ProductCollectionResult(run_id, count, pages, total, previous_id)
