"""Полный обход производителей и товаров ProductCenter."""

import asyncio
import logging
import re
from collections.abc import AsyncIterator
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
from src.adapter.supplier.productcenter_web.progress import CrawlProgress
from src.adapter.supplier.productcenter_web.request import RequestPacer, get
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
        max_concurrent: int = 1,
        http_timeout: float = 30.0,
        max_cards: int | None = None,
        retries: int = 5,
        connection_retries: int = 180,
        request_interval: float = 1.0,
        cache_dir: Path | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._source = source_defaults
        self._max_concurrent = max(1, max_concurrent)
        self._http_timeout = http_timeout
        self._max_cards = max_cards
        self._retries = retries
        self._connection_retries = max(0, connection_retries)
        self._request_interval = max(0.0, request_interval)
        self._pacer = RequestPacer(self._request_interval)
        self._transport = transport
        self._cache = PageCache(cache_dir) if cache_dir is not None else None
        self.stats: dict[str, int] = {}
        self._progress = CrawlProgress(cache_dir)

    @property
    def source(self) -> Source:
        return self._source

    async def resume(self, started_at: datetime) -> datetime:
        return await self._progress.resume(started_at)

    @property
    def saved_offer_count(self) -> int:
        return len(self._progress.products)

    async def complete(self) -> None:
        await self._progress.complete()

    async def _get(self, http: httpx.AsyncClient, url: str) -> httpx.Response:
        return await get(
            http,
            url,
            self._retries,
            self._cache,
            connection_retries=self._connection_retries,
            pacer=self._pacer,
        )

    async def batches(self, batch_size: int) -> AsyncIterator[SupplierPackage]:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if self._max_cards is not None:
            raise ContentFormatError("Диагностический лимит запрещён для потоковой записи")
        self.stats = {}
        self._pacer = RequestPacer(self._request_interval)
        suppliers: dict[str, Supplier] = {}
        seen = self._progress.products
        failures: list[str] = []
        now = self._progress.started_at or datetime.now(UTC)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._http_timeout),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            transport=self._transport,
        ) as http:

            async def packages(urls: dict[str, str]):
                pending = [(key, url) for key, url in urls.items() if key not in seen]
                for offset in range(0, len(pending), batch_size):
                    group = dict(pending[offset : offset + batch_size])
                    offers = await self._fetch_cards(
                        http, group, product_card, now, failures=failures
                    )
                    missing = {}
                    for offer in offers.values():
                        key = card_key(offer.evidence_url, "producers")
                        if key is None:
                            raise ContentFormatError("Товар без ссылки на производителя")
                        if key not in suppliers:
                            missing[key] = offer.evidence_url
                    suppliers.update(
                        await self._fetch_cards(http, missing, supplier_card, failures=failures)
                    )
                    linked = []
                    owners = {}
                    for offer in offers.values():
                        supplier = suppliers.get(card_key(offer.evidence_url, "producers"))
                        if supplier is None:
                            continue
                        owners[supplier.supplier_id] = supplier
                        linked.append(replace(offer, supplier_id=supplier.supplier_id))
                    if linked:
                        yield SupplierPackage(self._source, tuple(owners.values()), tuple(linked))
                        seen.update(offer.external_id for offer in linked)
                        self._progress.producers.update(
                            card_key(offer.evidence_url, "producers") for offer in linked
                        )
                        await self._progress.save()

            async for urls in self._listing_pages(http, "products", progress=True):
                async for package in packages(urls):
                    yield package
            cards = await sitemap_cards(
                http,
                self._retries,
                self._cache,
                connection_retries=self._connection_retries,
                pacer=self._pacer,
            )
            async for package in packages(cards["products"]):
                yield package
            producers = {}
            async for found in self._listing_pages(http, "producers", progress=True):
                producers.update(found)
            producers.update(cards["producers"])
            pending = [
                (key, url) for key, url in producers.items() if key not in self._progress.producers
            ]
            for offset in range(0, len(pending), batch_size):
                found = await self._fetch_cards(
                    http,
                    dict(pending[offset : offset + batch_size]),
                    supplier_card,
                    failures=failures,
                )
                suppliers.update(found)
                if found:
                    yield SupplierPackage(self._source, tuple(found.values()))
                    self._progress.producers.update(found)
                    await self._progress.save()
            if failures:
                raise ContentFormatError(
                    f"ProductCenter: не прочитано карточек {len(failures)}; первая: {failures[0]}"
                )

    async def fetch(self) -> SupplierPackage:
        self.stats = {}
        self._pacer = RequestPacer(self._request_interval)
        if self._cache is not None:
            self._cache.hits = 0
            self._cache.writes = 0
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._http_timeout),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            transport=self._transport,
        ) as http:
            cards = await sitemap_cards(
                http,
                self._retries,
                self._cache,
                connection_retries=self._connection_retries,
                pacer=self._pacer,
            )
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
                match = _PRODUCER_KEY.match(urlsplit(offer.evidence_url).path)
                if match is None or match.group(1) not in supplier_by_key:
                    missing.add(offer.evidence_url)
            if missing:
                extra = {card_key(url, "producers"): url for url in missing}
                if None in extra:
                    raise ContentFormatError("Товар ссылается на неверную карточку производителя")
                supplier_by_key.update(await self._fetch_cards(http, extra, supplier_card))
            linked: list[Offer] = []
            for offer in offers.values():
                match = _PRODUCER_KEY.match(urlsplit(offer.evidence_url).path)
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
        result = {}
        async for found in self._listing_pages(http, kind):
            result.update(found)
        return result

    async def _listing_pages(
        self, http: httpx.AsyncClient, kind: str, *, progress: bool = False
    ) -> AsyncIterator[dict[str, str]]:
        first_url = f"{BASE_URL}/{kind}"
        saved = self._progress.listings.setdefault(kind, {}) if progress else {}
        if saved:
            first = dict(saved["pages"]["1"])
            last_page = saved["last"]
        else:
            first_response = await self._get(http, first_url)
            try:
                first_tree = await asyncio.to_thread(page.parse, first_response.text, first_url)
                first, last_page, current_page = listing_links(first_tree, kind)
                if current_page != 1:
                    raise ContentFormatError(
                        f"{first_url}: получена страница {current_page} вместо 1"
                    )
            except Exception:
                if self._cache is not None:
                    await self._cache.invalidate(first_url)
                raise
            saved.update(last=last_page, pages={"1": dict(first)})
        if last_page < 2:
            raise ContentFormatError(f"{first_url}: не обнаружена пагинация")
        logger.info("ProductCenter %s: страниц списка %d", kind, last_page)
        self.stats[f"listing_pages_{kind}"] = last_page
        pages = (f"{first_url}/page-{number}" for number in range(2, last_page + 1))

        async def read_listing(url: str) -> tuple[dict[str, str], int, int]:
            response = await self._get(http, url)
            try:
                tree = await asyncio.to_thread(page.parse, response.text, url)
                return listing_links(tree, kind)
            except Exception:
                if self._cache is not None:
                    await self._cache.invalidate(url)
                raise

        yield dict(first)
        seen_pages = {frozenset(first)}
        page_size = len(first)
        for expected_page, url in enumerate(pages, start=2):
            stored = saved["pages"].get(str(expected_page))
            if stored is None:
                found, observed_last, observed_page = await read_listing(url)
            else:
                found, observed_last, observed_page = stored, last_page, expected_page
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
            saved["pages"][str(expected_page)] = found
            yield found

    async def _fetch_cards(
        self,
        http: httpx.AsyncClient,
        urls: dict[str, str],
        parser,
        *args,
        failures: list[str] | None = None,
    ):
        async def read_card(item: tuple[str, str]):
            key, url = item
            try:
                response = await self._get(http, url)
                parsed = await asyncio.to_thread(
                    parser, response.text, url, self._source.source_id, *args
                )
            except Exception as error:
                if self._cache is not None:
                    await self._cache.invalidate(url)
                if failures is None:
                    raise
                failures.append(url)
                logger.warning(
                    "ProductCenter: пропущена карточка %s: %s", url, type(error).__name__
                )
                return None
            return key, parsed

        results = await self._bounded(iter(urls.items()), read_card, parser.__name__)
        return dict(item for item in results if item is not None)

    async def _bounded(self, items, read, stage: str):
        iterator = enumerate(items)
        results = {}

        async def worker():
            while True:
                try:
                    index, item = next(iterator)
                except StopIteration:
                    return
                results[index] = await read(item)
                self.stats[f"read_{stage.replace(' ', '_')}"] = len(results)
                if len(results) % 1000 == 0:
                    logger.info("ProductCenter %s: обработано %d", stage, len(results))

        async with asyncio.TaskGroup() as group:
            for _ in range(self._max_concurrent):
                group.create_task(worker())
        return [results[index] for index in range(len(results))]
