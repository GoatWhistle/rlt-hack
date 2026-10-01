"""Полный обход производителей и товаров ProductCenter."""

import asyncio
import logging
import re
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from src.adapter.supplier import page
from src.adapter.supplier.errors import ContentFormatError
from src.adapter.supplier.productcenter_web.cache import PageCache
from src.adapter.supplier.productcenter_web.discovery import (
    BASE_URL,
    card_key,
    listing_links,
    sitemap_cards,
)
from src.adapter.supplier.productcenter_web.parse import product_card, supplier_card
from src.adapter.supplier.productcenter_web.request import get
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier

logger = logging.getLogger(__name__)
PROVIDER_NAME = "productcenter_web"
USER_AGENT = "rlt-supplier-search/0.1 (+contact: see deployment configuration)"
_PRODUCER_KEY = re.compile(r"^/producers/(\d+)/")


class ProductCenterWebProvider:
    def __init__(
        self,
        source_defaults: Source,
        max_concurrent: int = 4,
        http_timeout: float = 30.0,
        max_cards: int | None = None,
        retries: int = 5,
        cache_dir: Path | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._source = source_defaults
        self._max_concurrent = max(1, max_concurrent)
        self._http_timeout = http_timeout
        self._max_cards = max_cards
        self._retries = retries
        self._transport = transport
        self._cache = PageCache(cache_dir) if cache_dir is not None else None
        self.stats: dict[str, int] = {}

    @property
    def source(self) -> Source:
        return self._source

    async def fetch(self) -> SupplierPackage:
        self.stats = {}
        if self._cache is not None:
            self._cache.hits = 0
            self._cache.writes = 0
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._http_timeout),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            transport=self._transport,
        ) as http:
            cards = await sitemap_cards(http, self._retries, self._cache)
            self.stats["sitemap_producers"] = len(cards["producers"])
            self.stats["sitemap_products"] = len(cards["products"])
            for kind in ("producers", "products"):
                listed = await self._listing_cards(http, kind)
                self.stats[f"listing_{kind}"] = len(listed)
                for key, url in listed.items():
                    cards[kind].setdefault(key, url)
                self.stats[f"discovered_{kind}"] = len(cards[kind])
                logger.info(
                    "ProductCenter %s: sitemap + lists = %d cards, lists = %d",
                    kind,
                    len(cards[kind]),
                    len(listed),
                )
            total = sum(len(group) for group in cards.values())
            if self._max_cards is not None and total > self._max_cards:
                raise ContentFormatError(
                    f"ProductCenter: найдено {total} карточек, диагностический лимит "
                    f"{self._max_cards}; неполный пакет не публикуется"
                )
            suppliers = await self._fetch_cards(http, cards["producers"], supplier_card)
            supplier_by_key = {key: supplier for key, supplier in suppliers.items()}
            now = datetime.now(UTC)
            offers = await self._fetch_cards(http, cards["products"], product_card, now)
            missing: set[str] = set()
            for offer in offers.values():
                match = _PRODUCER_KEY.match(urlsplit(offer.seller_evidence_url).path)
                if match is None or match.group(1) not in supplier_by_key:
                    missing.add(offer.seller_evidence_url)
            if missing:
                extra = {card_key(url, "producers"): url for url in missing}
                if None in extra:
                    raise ContentFormatError("Товар ссылается на неверную карточку производителя")
                supplier_by_key.update(await self._fetch_cards(http, extra, supplier_card))
            linked: list[Offer] = []
            for offer in offers.values():
                match = _PRODUCER_KEY.match(urlsplit(offer.seller_evidence_url).path)
                supplier = supplier_by_key.get(match.group(1)) if match else None
                if supplier is None:
                    raise ContentFormatError(f"{offer.url}: не найдена карточка производителя")
                linked.append(replace(offer, supplier_id=supplier.supplier_id))
            unique_suppliers: dict[str, Supplier] = {}
            for key in sorted(supplier_by_key, key=int):
                supplier = supplier_by_key[key]
                unique_suppliers.setdefault(str(supplier.supplier_id), supplier)
            linked.sort(key=lambda offer: int(offer.external_id))
            logger.info(
                "ProductCenter: компаний %d, товаров %d, ИНН %d, связей %d",
                len(unique_suppliers),
                len(linked),
                sum(bool(s.inn) for s in unique_suppliers.values()),
                len(linked),
            )
            if self._cache is not None:
                self.stats["cache_hits"] = self._cache.hits
                self.stats["cache_writes"] = self._cache.writes
            return SupplierPackage(self._source, tuple(unique_suppliers.values()), tuple(linked))

    async def _listing_cards(self, http: httpx.AsyncClient, kind: str) -> dict[str, str]:
        first_url = f"{BASE_URL}/{kind}"
        first_response = await get(http, first_url, self._retries, self._cache)
        try:
            first_tree = await asyncio.to_thread(page.parse, first_response.text, first_url)
            first, last_page, current_page = listing_links(first_tree, kind)
            if current_page != 1:
                raise ContentFormatError(f"{first_url}: получена страница {current_page} вместо 1")
        except Exception:
            if self._cache is not None:
                await self._cache.invalidate(first_url)
            raise
        if last_page < 2:
            raise ContentFormatError(f"{first_url}: не обнаружена пагинация")
        logger.info("ProductCenter %s: страниц списка %d", kind, last_page)
        self.stats[f"listing_pages_{kind}"] = last_page
        pages = (f"{first_url}/page-{number}" for number in range(2, last_page + 1))

        async def read_listing(url: str) -> tuple[dict[str, str], int, int]:
            response = await get(http, url, self._retries, self._cache)
            try:
                tree = await asyncio.to_thread(page.parse, response.text, url)
                return listing_links(tree, kind)
            except Exception:
                if self._cache is not None:
                    await self._cache.invalidate(url)
                raise

        results = await self._bounded(pages, read_listing, f"{kind} list")
        seen_pages = {frozenset(first)}
        page_size = len(first)
        for expected_page, (found, observed_last, observed_page) in enumerate(results, start=2):
            url = f"{first_url}/page-{expected_page}"
            if observed_page != expected_page:
                if self._cache is not None:
                    await self._cache.invalidate(url)
                raise ContentFormatError(
                    f"{kind}: ожидалась страница {expected_page}, получена {observed_page}"
                )
            if observed_last != last_page:
                if self._cache is not None:
                    await self._cache.invalidate(url)
                raise ContentFormatError(f"{kind}: пагинация изменилась во время обхода")
            ids = frozenset(found)
            if ids in seen_pages:
                if self._cache is not None:
                    await self._cache.invalidate(url)
                raise ContentFormatError(
                    f"{kind}: повторился набор карточек страницы {expected_page}"
                )
            if (expected_page < last_page and len(ids) != page_size) or (
                expected_page == last_page and len(ids) > page_size
            ):
                if self._cache is not None:
                    await self._cache.invalidate(url)
                raise ContentFormatError(
                    f"{kind}: неверное число карточек страницы {expected_page}"
                )
            if ids.intersection(first):
                if self._cache is not None:
                    await self._cache.invalidate(url)
                raise ContentFormatError(
                    f"{kind}: карточки повторились на странице {expected_page}"
                )
            seen_pages.add(ids)
            first.update(found)
        return first

    async def _fetch_cards(self, http: httpx.AsyncClient, urls: dict[str, str], parser, *args):
        async def read_card(item: tuple[str, str]):
            key, url = item
            response = await get(http, url, self._retries, self._cache)
            try:
                parsed = await asyncio.to_thread(
                    parser, response.text, url, self._source.source_id, *args
                )
            except Exception:
                if self._cache is not None:
                    await self._cache.invalidate(url)
                raise
            return key, parsed

        return dict(await self._bounded(iter(urls.items()), read_card, parser.__name__))

    async def _bounded(self, items, read, stage: str):
        iterator = iter(items)
        results = []

        async def worker():
            while True:
                try:
                    item = next(iterator)
                except StopIteration:
                    return
                results.append(await read(item))
                self.stats[f"read_{stage.replace(' ', '_')}"] = len(results)
                if len(results) % 1000 == 0:
                    logger.info("ProductCenter %s: обработано %d", stage, len(results))

        async with asyncio.TaskGroup() as group:
            for _ in range(self._max_concurrent):
                group.create_task(worker())
        return results
