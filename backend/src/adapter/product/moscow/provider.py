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
CARD_URL = "https://zakupki.mos.ru/classifier/api/Sku/GetSku"
CATEGORY_URL = "https://zakupki.mos.ru/classifier/api/ProductionDirectory/GetDirectoryLightChain"


@dataclass(frozen=True, slots=True)
class ProductPage:
    total: int
    items: tuple[Product, ...]


class MoscowProductProvider:
    def __init__(
        self,
        source_id: UUID,
        *,
        page_size: int = 500,
        timeout: float = 30.0,
        max_concurrent: int = 4,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if page_size < 1 or max_concurrent < 1:
            raise ValueError("page_size and max_concurrent must be positive")
        self.source_id = source_id
        self.page_size = page_size
        self.timeout = timeout
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._categories: dict[str, tuple[str, ...]] = {}
        self._client = client

    async def fetch_page(
        self,
        offset: int,
        client: httpx.AsyncClient,
        *,
        descending: bool = False,
        take: int | None = None,
    ) -> ProductPage:
        requested = take or self.page_size
        query = {
            "skip": offset,
            "take": requested,
            "withCount": True,
            "order": [{"field": "id", "desc": descending}],
        }
        response = await self._request(
            client, INDEX_URL, {"queryFilter": json.dumps(query, separators=(",", ":"))}
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
        if len(raw_items) > requested:
            raise MoscowProductFormatError("страница длиннее запрошенного take")
        if any(not isinstance(item, Mapping) for item in raw_items):
            raise MoscowProductFormatError("элемент СТЕ не объект")
        return ProductPage(total, tuple(parse_product(self.source_id, item) for item in raw_items))

    async def _request(
        self, client: httpx.AsyncClient, url: str, params: dict[str, str]
    ) -> httpx.Response:
        for attempt in range(4):
            try:
                response = await client.get(url, params=params)
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
                    yield await self._enrich(page, client)
        else:
            async for page in self._pages(self._client):
                yield await self._enrich(page, self._client)

    async def listing_pages(self) -> AsyncIterator[ProductPage]:
        if self._client is None:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                async for page in self._pages(client):
                    yield page
        else:
            async for page in self._pages(self._client):
                yield page

    async def _enrich(self, page: ProductPage, client: httpx.AsyncClient) -> ProductPage:
        cards = await asyncio.gather(*(self._fetch_card(item, client) for item in page.items))
        return ProductPage(page.total, tuple(cards))

    async def _fetch_card(self, listed: Product, client: httpx.AsyncClient) -> Product:
        async with self._semaphore:
            response = await self._request(
                client,
                CARD_URL,
                {"id": listed.external_id, "withRegionPriceStatistics": "false"},
            )
            if response.status_code in (403, 404):
                return listed
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as error:
                raise MoscowProductFormatError("карточка СТЕ вернула не JSON") from error
            if not isinstance(payload, Mapping):
                raise MoscowProductFormatError("карточка СТЕ не объект")
            if str(payload.get("id")) != listed.external_id:
                raise MoscowProductIncompleteError("ID карточки не совпадает со списком")
            directory_id = payload.get("productionDirectoryId")
            category_path = await self._category_path(directory_id, client)
            return parse_product(self.source_id, payload, category_path, full_card=True)

    async def _category_path(
        self, identifier: object, client: httpx.AsyncClient
    ) -> tuple[str, ...]:
        if not isinstance(identifier, int):
            return ()
        key = str(identifier)
        if key in self._categories:
            return self._categories[key]
        response = await self._request(client, CATEGORY_URL, {"directoryId": key})
        response.raise_for_status()
        try:
            chain = response.json()
        except ValueError as error:
            raise MoscowProductFormatError("иерархия категории вернула не JSON") from error
        if not isinstance(chain, list):
            raise MoscowProductFormatError("иерархия категории не массив")
        if not chain:
            self._categories[key] = ()
            return ()
        if not all(
            isinstance(part, Mapping) and isinstance(part.get("name"), str) for part in chain
        ):
            raise MoscowProductFormatError("неверный формат иерархии категории")
        if chain[-1].get("id") != identifier:
            raise MoscowProductIncompleteError("иерархия не соответствует категории СТЕ")
        path = tuple(part["name"] for part in chain)
        self._categories[key] = path
        return path

    async def sample(self) -> ProductPage:
        if self._client is not None:
            return await self.fetch_page(0, self._client)
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            return await self.fetch_page(0, client)

    async def card(self, listed: Product) -> Product:
        if self._client is not None:
            return await self._fetch_card(listed, self._client)
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            return await self._fetch_card(listed, client)

    async def _pages(self, client: httpx.AsyncClient) -> AsyncIterator[ProductPage]:
        first = await self.fetch_page(0, client)
        total = first.total
        ascending_target = max(min(total, self.page_size), (total + 1) // 2)
        descending_target = total - ascending_target
        offset = 0
        previous_id: int | None = None
        page = first
        while offset < ascending_target:
            if page.total != total:
                raise MoscowProductIncompleteError("число СТЕ изменилось во время обхода")
            requested = min(self.page_size, ascending_target - offset)
            if len(page.items) != requested:
                raise MoscowProductIncompleteError("неполная страница СТЕ в прямом обходе")
            previous_id = self._check_order(page.items, previous_id, descending=False)
            offset += len(page.items)
            yield page
            if offset < ascending_target:
                requested = min(self.page_size, ascending_target - offset)
                page = await self.fetch_page(offset, client, take=requested)
        ascending_max = previous_id
        offset = 0
        previous_id = None
        while offset < descending_target:
            requested = min(self.page_size, descending_target - offset)
            page = await self.fetch_page(offset, client, descending=True, take=requested)
            if page.total != total or len(page.items) != requested:
                raise MoscowProductIncompleteError("неполная страница СТЕ в обратном обходе")
            previous_id = self._check_order(page.items, previous_id, descending=True)
            if (
                ascending_max is not None
                and previous_id is not None
                and previous_id <= ascending_max
            ):
                raise MoscowProductIncompleteError("половины каталога СТЕ пересеклись")
            offset += len(page.items)
            yield page

    @staticmethod
    def _check_order(
        items: tuple[Product, ...], previous: int | None, *, descending: bool
    ) -> int | None:
        for product in items:
            try:
                current = int(product.external_id)
            except ValueError as error:
                raise MoscowProductFormatError("ID СТЕ не число") from error
            if previous is not None and (
                (descending and current >= previous) or (not descending and current <= previous)
            ):
                raise MoscowProductIncompleteError("повтор или нарушение сортировки СТЕ по ID")
            previous = current
        return previous
