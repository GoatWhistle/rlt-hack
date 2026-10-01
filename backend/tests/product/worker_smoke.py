"""Снимок продуктов публикуется только после двух одинаковых обходов."""

import asyncio
import sys
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.product.moscow.parse import parse_product
from src.models.product import Product
from src.service.product.worker import ProductSyncWorker


@dataclass(frozen=True)
class Page:
    total: int
    items: tuple[Product, ...]


class Provider:
    def __init__(self, traversals: list[list[Page]]) -> None:
        self.source_id = uuid4()
        self.traversals = traversals

    async def pages(self) -> AsyncIterator[Page]:
        for page in self.traversals.pop(0):
            yield page

    async def listing_pages(self) -> AsyncIterator[Page]:
        for page in self.traversals.pop(0):
            yield page


class Storage:
    def __init__(self) -> None:
        self.staged: list[Product] = []
        self.published: list[tuple[UUID, UUID, int]] = []

    async def stage(self, run_id: UUID, products: Sequence[Product]) -> None:
        self.staged.extend(products)

    async def publish(self, run_id: UUID, source_id: UUID, expected: int) -> None:
        self.published.append((run_id, source_id, expected))


async def main() -> None:
    source = uuid4()
    first = parse_product(source, {"id": 1, "name": "Товар"})
    changed = parse_product(source, {"id": 1, "name": "Другое название"})
    storage = Storage()
    stable_provider = Provider([[Page(1, (first,))], [Page(1, (first,))]])
    result = await ProductSyncWorker(stable_provider, storage).run_once()
    assert result.product_count == 1 and len(storage.published) == 1
    assert result.pages_fetched == 2 and not result.names_changed
    assert result.summary_only_count == 1
    assert storage.staged == [first]

    storage = Storage()
    worker = ProductSyncWorker(Provider([[Page(1, (first,))], [Page(1, (changed,))]]), storage)
    result = await worker.run_once()
    assert result.names_changed and storage.staged == [changed]
    assert len(storage.published) == 1

    storage = Storage()
    other = parse_product(source, {"id": 2, "name": "Другой товар"})
    worker = ProductSyncWorker(Provider([[Page(1, (first,))], [Page(1, (other,))]]), storage)
    try:
        await worker.run_once()
    except ValueError as error:
        assert "состав" in str(error)
    else:
        raise AssertionError("изменившийся снимок опубликован")
    assert storage.staged == [other] and storage.published == []

    storage = Storage()
    try:
        await ProductSyncWorker(Provider([[Page(0, ())]]), storage).run_once()
    except ValueError:
        pass
    else:
        raise AssertionError("пустой снимок опубликован")
    assert storage.published == []


if __name__ == "__main__":
    asyncio.run(main())
