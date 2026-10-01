"""Интерфейсы, необходимые сервису публикации каталога продуктов."""

from collections.abc import AsyncIterator, Sequence
from typing import Protocol
from uuid import UUID

from src.models.product import Product


class ProductPage(Protocol):
    @property
    def total(self) -> int: ...

    @property
    def items(self) -> tuple[Product, ...]: ...


class ProductProvider(Protocol):
    @property
    def source_id(self) -> UUID: ...

    def pages(self) -> AsyncIterator[ProductPage]: ...

    def listing_pages(self) -> AsyncIterator[ProductPage]: ...

    def collect_pages(
        self, offset: int, previous_id: int | None, max_pages: int
    ) -> AsyncIterator[ProductPage]: ...


class ProductStorage(Protocol):
    async def stage(self, run_id: UUID, products: Sequence[Product]) -> None: ...

    async def publish(self, run_id: UUID, source_id: UUID, expected: int) -> None: ...

    async def collection_progress(
        self, run_id: UUID, source_id: UUID
    ) -> tuple[int, int | None]: ...
