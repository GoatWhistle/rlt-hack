"""Постраничное чтение публичного индекса СТЕ."""

import asyncio
import json
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from uuid import UUID

import httpx

from src.adapter.product.moscow.errors import (
    MoscowProductFormatError,
    MoscowProductIncompleteError,
)
from src.adapter.product.moscow.parse import parse_product
from src.models.product import Product

INDEX_URL = "https://zakupki.mos.ru/newapi/api/Sku/QueryIndex"


@dataclass(frozen=True, slots=True)
class ProductPage:
    total: int
    items: tuple[Product, ...]


class MoscowProductProvider:
    def __init__(
        self,
        source_id: UUID,
        *,
        page_size: int = 100,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if page_size < 1:
            raise ValueError("page_size must be positive")
        self.source_id = source_id
        self.page_size = page_size
        self.timeout = timeout
        self._client = client

    async def fetch_page(self, offset: int, client: httpx.AsyncClient) -> ProductPage:
        query = {
            "skip": offset,
            "take": self.page_size,
            "withCount": True,
            "order": [{"field": "id", "desc": False}],
        }
        response = await self._request(
            client, {"queryFilter": json.dumps(query, separators=(",", ":"))}
        )
        response.raise_for_status()
        try:
            document = response.json()
        except ValueError as error:
            raise MoscowProductFormatError("индекс СТЕ вернул не JSON") from error
        if not isinstance(document, Mapping):
            raise MoscowProductFormatError("ответ индекса СТЕ не объект")
        total = document.get("count")
        raw_items = document.get("items")
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise MoscowProductFormatError("отсутствует корректный count")
        if not isinstance(raw_items, list):
            raise MoscowProductFormatError("отсутствует массив items")
        if len(raw_items) > self.page_size:
            raise MoscowProductFormatError("страница длиннее запрошенного take")
        if any(not isinstance(item, Mapping) for item in raw_items):
            raise MoscowProductFormatError("элемент СТЕ не объект")
        return ProductPage(total, tuple(parse_product(self.source_id, item) for item in raw_items))

    async def _request(self, client: httpx.AsyncClient, params: dict[str, str]) -> httpx.Response:
        for attempt in range(4):
            try:
                response = await client.get(INDEX_URL, params=params)
                if response.status_code not in (429, 500, 502, 503, 504):
                    return response
                response.raise_for_status()
            except (httpx.TransportError, httpx.HTTPStatusError):
                if attempt == 3:
                    raise
            await asyncio.sleep(min(2**attempt, 8))
        raise AssertionError("недостижимая ветка повторов")

    async def pages(self) -> AsyncIterator[ProductPage]:
        if self._client is None:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                async for page in self._pages(client):
                    yield page
        else:
            async for page in self._pages(self._client):
                yield page

    async def _pages(self, client: httpx.AsyncClient) -> AsyncIterator[ProductPage]:
        offset = 0
        total: int | None = None
        previous_id: int | None = None
        while total is None or offset < total:
            page = await self.fetch_page(offset, client)
            if total is None:
                total = page.total
            elif page.total != total:
                raise MoscowProductIncompleteError("число СТЕ изменилось во время обхода")
            if not page.items and offset < total:
                raise MoscowProductIncompleteError("индекс вернул пустую промежуточную страницу")
            if offset + len(page.items) < total and len(page.items) != self.page_size:
                raise MoscowProductIncompleteError("неполная промежуточная страница СТЕ")
            for product in page.items:
                try:
                    current_id = int(product.external_id)
                except ValueError as error:
                    raise MoscowProductFormatError("ID СТЕ не число") from error
                if previous_id is not None and current_id <= previous_id:
                    raise MoscowProductIncompleteError("повтор или нарушение сортировки СТЕ по ID")
                previous_id = current_id
            offset += len(page.items)
            yield page
        if offset != total:
            raise MoscowProductIncompleteError("число прочитанных СТЕ не совпадает с count")
