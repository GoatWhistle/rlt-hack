"""Полный обход товаров и продавцов Supl.biz по sitemap.

Перечень страниц источник публикует сам: корневой `sitemap.xml` ведёт на
постраничные `sitemap-proposals.xml?p=N` (по 500 товаров) и на `sitemap-users.xml`
с профилями компаний. Страница товара содержит состояние `preloadedState` с
товаром и продавцом, страница профиля — с реквизитами и контактами. Так
собираются и продавцы с товарами, и продавцы без опубликованных товаров.

Закрыты в `robots.txt` разделы `/profiles/` и `/api/`: адаптер читает только
страницы товаров и профилей `/profile-<id>/` из sitemap. Любая неполученная
часть перечня или служебный ответ вместо sitemap завершают обход ошибкой:
неполный снимок снял бы ранее собранные предложения с продажи.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.supl_biz_web import sitemap
from src.adapter.supplier.supl_biz_web.balanced import RootPlan, allocate
from src.adapter.supplier.supl_biz_web.categories import parse_listing, parse_tree
from src.adapter.supplier.supl_biz_web.request import get
from src.adapter.supplier.supl_biz_web.state import (
    BASE_URL,
    ProfileCard,
    ProposalCard,
    merge_suppliers,
    parse_profile,
    parse_proposal,
)
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier

logger = logging.getLogger(__name__)

PROVIDER_NAME = "supl_biz_web"

SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

# Значение заголовка обязано быть ASCII: контакт указывается при развёртывании.
USER_AGENT = "rlt-supplier-search/0.1 (+contact: see deployment configuration)"

_PROPOSAL_SITEMAP = "sitemap-proposals.xml"
_USER_SITEMAP = "sitemap-users.xml"

PAGE_SIZE = 500

TREE_URL = f"{BASE_URL}/proposals/"


@dataclass(frozen=True, slots=True)
class CategoryShare:
    """Итог выборки по одной корневой категории."""

    name: str
    requested: int
    listed: int
    fetched: int
    confirmed: int


@dataclass(frozen=True, slots=True)
class BalancedSample:
    package: SupplierPackage
    shares: tuple[CategoryShare, ...]


class SuplBizWebProvider:
    """Читает товары и профили из sitemap и собирает пакет компаний и предложений."""

    def __init__(
        self,
        source_defaults: Source,
        sitemap_url: str = SITEMAP_URL,
        max_cards: int | None = None,
        max_concurrent: int = 4,
        http_timeout: float = 30.0,
        retries: int = 4,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._source = source_defaults
        self._sitemap_url = sitemap_url
        self._max_cards = max_cards
        self._max_concurrent = max(1, max_concurrent)
        self._http_timeout = http_timeout
        self._retries = retries
        self._transport = transport

    @property
    def source(self) -> Source:
        return self._source

    async def fetch(self) -> SupplierPackage:
        async with self._client() as http:
            files = await self._sitemap_files(http)
            proposals = await self._listed(http, files[_PROPOSAL_SITEMAP])
            profiles = await self._listed(http, files[_USER_SITEMAP])
            total = len(proposals) + len(profiles)
            if self._max_cards is not None and total > self._max_cards:
                raise ContentFormatError(
                    f"Supl.biz: найдено {total} страниц, диагностический лимит "
                    f"{self._max_cards}; неполный пакет не публикуется"
                )
            return await self._package(http, proposals, profiles)

    async def sample(self, limit: int) -> SupplierPackage:
        """Диагностический пакет из первых товаров sitemap: не полный снимок.

        Предназначен для проверки разбора на живом источнике. Worker его не
        вызывает, а сохранять такой пакет в хранилище нельзя.
        """
        async with self._client() as http:
            files = await self._sitemap_files(http)
            first = files[_PROPOSAL_SITEMAP][: -(-limit // PAGE_SIZE)]
            proposals = await self._listed(http, first)
            return await self._package(http, proposals[:limit], [])

    async def balanced_sample(self, per_category: int) -> BalancedSample:
        """Диагностический пакет: поровну товаров на каждую корневую категорию.

        Внутри категории товары берутся по кругу из её подкатегорий. Выборка
        неполная: worker её не вызывает, а сохранять её как снимок источника
        нельзя. Если в категории меньше товаров, чем квота, это видно в `shares`.
        """
        if per_category < 1:
            raise ValueError("per_category должен быть положительным")
        async with self._client() as http:
            tree = await get(http, TREE_URL, self._retries)
            if tree is None:
                raise SourceUnavailableError(f"{TREE_URL}: страница с категориями не найдена")
            roots = await asyncio.to_thread(parse_tree, tree.text, TREE_URL)
            taken: set[str] = set()
            plans: list[RootPlan] = []
            for root in roots:
                listings = await self._bounded(
                    root.children, lambda child: self._listing(http, child.url)
                )
                plans.append(allocate(root, listings, per_category, taken))
            urls = [url for plan in plans for url in plan.urls]
            logger.info("Supl.biz: категорий %d, товаров к чтению %d", len(roots), len(urls))
            package = await self._package(http, urls, [])
        return BalancedSample(package, self._shares(plans, package, per_category))

    async def _listing(self, http: httpx.AsyncClient, url: str) -> list[str]:
        response = await get(http, url, self._retries)
        if response is None:
            raise SourceUnavailableError(f"{url}: категория исчезла во время обхода")
        return await asyncio.to_thread(parse_listing, response.text, url)

    def _shares(
        self, plans: list[RootPlan], package: SupplierPackage, quota: int
    ) -> tuple[CategoryShare, ...]:
        fetched = {offer.external_id: offer for offer in package.offers}
        shares = []
        for plan in plans:
            offers = [fetched[i] for i in map(_proposal_id, plan.urls) if i in fetched]
            confirmed = sum(_names_category(offer, plan.root.name) for offer in offers)
            shares.append(
                CategoryShare(plan.root.name, quota, len(plan.urls), len(offers), confirmed)
            )
        return tuple(shares)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self._http_timeout),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            transport=self._transport,
        )

    async def _sitemap_files(self, http: httpx.AsyncClient) -> dict[str, list[str]]:
        index = await get(http, self._sitemap_url, self._retries)
        if index is None:
            raise SourceUnavailableError(f"{self._sitemap_url}: sitemap не найден")
        listed = await asyncio.to_thread(
            sitemap.locations, index.content, self._sitemap_url, sitemap.INDEX
        )
        files: dict[str, list[str]] = {_PROPOSAL_SITEMAP: [], _USER_SITEMAP: []}
        for location in listed:
            name = urlsplit(location).path.rsplit("/", 1)[-1]
            if name in files:
                files[name].append(location)
        for name, found in files.items():
            if not found:
                raise SourceUnavailableError(f"{self._sitemap_url}: нет файлов {name}")
        logger.info(
            "Supl.biz: файлов sitemap — товаров %d, профилей %d",
            len(files[_PROPOSAL_SITEMAP]),
            len(files[_USER_SITEMAP]),
        )
        return files

    async def _listed(self, http: httpx.AsyncClient, files: list[str]) -> list[str]:
        parts = await self._bounded(files, lambda url: self._read_sitemap(http, url))
        return list(dict.fromkeys(url for part in parts for url in part))

    async def _read_sitemap(self, http: httpx.AsyncClient, url: str) -> list[str]:
        response = await get(http, url, self._retries)
        if response is None:
            raise SourceUnavailableError(f"{url}: файл sitemap исчез во время обхода")
        return await asyncio.to_thread(sitemap.locations, response.content, url, sitemap.URLSET)

    async def _package(
        self, http: httpx.AsyncClient, proposals: list[str], profiles: list[str]
    ) -> SupplierPackage:
        now = datetime.now(UTC)
        cards = await self._bounded(proposals, lambda url: self._proposal(http, url, now))
        cards_of_profiles = await self._bounded(profiles, lambda url: self._profile(http, url))
        found = [card for card in cards if card is not None]
        owners = [card for card in cards_of_profiles if card is not None]
        suppliers, offers = self._merge(found, owners)
        logger.info(
            "Supl.biz: товаров %d (исчезло %d), профилей %d (исчезло %d), "
            "компаний %d, предложений %d, ИНН %d",
            len(proposals),
            len(proposals) - len(found),
            len(profiles),
            len(profiles) - len(owners),
            len(suppliers),
            len(offers),
            sum(bool(supplier.inn) for supplier in suppliers),
        )
        return SupplierPackage(self._source, tuple(suppliers), tuple(offers))

    def _merge(
        self, proposals: list[ProposalCard], profiles: list[ProfileCard]
    ) -> tuple[list[Supplier], list[Offer]]:
        source_id = self._source.source_id
        by_key: dict[str, Supplier] = {}
        for card in proposals:
            by_key.setdefault(card.seller_key, card.supplier)
        for owner in profiles:
            known = by_key.get(owner.seller_key)
            by_key[owner.seller_key] = (
                merge_suppliers(owner.supplier, known, source_id, owner.seller_key)
                if known
                else owner.supplier
            )
        offers = [
            replace(card.offer, supplier_id=by_key[card.seller_key].supplier_id)
            for card in proposals
        ]
        unique = {str(supplier.supplier_id): supplier for supplier in by_key.values()}
        return list(unique.values()), offers

    async def _proposal(
        self, http: httpx.AsyncClient, url: str, now: datetime
    ) -> ProposalCard | None:
        response = await get(http, url, self._retries)
        if response is None:
            return None
        return await asyncio.to_thread(
            parse_proposal, response.text, str(response.url), self._source.source_id, now
        )

    async def _profile(self, http: httpx.AsyncClient, url: str) -> ProfileCard | None:
        response = await get(http, url, self._retries)
        if response is None:
            return None
        return await asyncio.to_thread(
            parse_profile, response.text, str(response.url), self._source.source_id
        )

    async def _bounded[T, R](
        self, items: Iterable[T], read: Callable[[T], Awaitable[R]]
    ) -> list[R]:
        """Читает элементы пулом воркеров: в памяти лишь число воркеров задач."""
        pending = iter(enumerate(items))
        results: dict[int, R] = {}

        async def worker() -> None:
            for index, item in pending:
                results[index] = await read(item)

        try:
            async with asyncio.TaskGroup() as group:
                for _ in range(self._max_concurrent):
                    group.create_task(worker())
        except ExceptionGroup as errors:
            raise errors.exceptions[0] from None
        return [results[index] for index in sorted(results)]


def _proposal_id(url: str) -> str:
    return url.rstrip("/").rsplit("-p", 1)[-1]


def _names_category(offer: Offer, name: str) -> bool:
    """Называет ли корневую категорию собственная разметка товара."""
    own = offer.source_category.split(" / ") + offer.attributes.get("categories", "").split(" | ")
    return name in own
