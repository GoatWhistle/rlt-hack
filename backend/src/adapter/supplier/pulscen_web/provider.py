"""Адаптер каталога Пульс цен (pulscen.ru).

Перечень рубрик берётся из sitemap: `sitemap_firms_rubrics.xml.gz` — рубрики
каталога компаний, `sitemap_price_N.xml.gz` — рубрики товаров. Каждая рубрика
читается по страницам до отсутствия `rel=next`: карточки компаний — из вёрстки,
товары с ценой — из JSON-LD `ItemList`.

Сайт защищён проверкой на робота. Адаптер её не обходит: ответ «Проверка
безопасности» завершает обход ошибкой, а доступ нужно получить у владельца
сайта. Пакет означает полный снимок, поэтому любая нечитаемая страница рубрики
тоже завершает обход ошибкой, а не публикует частичный результат.
"""

import asyncio
import logging
import time
from urllib.parse import urlsplit

import httpx

from src.adapter.supplier import page
from src.adapter.supplier.errors import BotProtectionError, SourceUnavailableError
from src.adapter.supplier.pulscen_web import parsing, sitemaps
from src.adapter.supplier.pulscen_web.builders import ModelBuilder
from src.models.package import SupplierPackage
from src.models.source import Source

logger = logging.getLogger(__name__)

PROVIDER_NAME = "pulscen_web"

BASE_URL = "https://www.pulscen.ru/"

SITEMAP_URL = "https://www.pulscen.ru/sitemap.xml"

FIRMS_PREFIX = "/firms/"

PRICE_PREFIX = "/price/"

# Значение заголовка обязано быть ASCII: контакт указывается при развёртывании.
USER_AGENT = "rlt-supplier-search/0.1 (+contact: see deployment configuration)"

# robots.txt задаёт Crawl-delay: 10 секунд между запросами.
DEFAULT_DELAY_SECONDS = 10.0


def _wanted_sitemap(url: str) -> bool:
    name = urlsplit(url).path.rsplit("/", 1)[-1]
    return name.startswith("sitemap_firms_rubrics") or (
        name.startswith("sitemap_price_") and "_f_" not in name and name != "sitemap_price_f.xml.gz"
    )


class PulscenWebProvider:
    """Обходит рубрики компаний и товаров, соблюдая паузу между запросами."""

    def __init__(
        self,
        source_defaults: Source,
        sitemap_url: str = SITEMAP_URL,
        delay_seconds: float = DEFAULT_DELAY_SECONDS,
        http_timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._source = source_defaults
        self._builder = ModelBuilder(source_defaults)
        self._sitemap_url = sitemap_url
        self._delay = max(0.0, delay_seconds)
        self._http_timeout = http_timeout
        self._transport = transport
        self._next_request_at = 0.0
        self._pace = asyncio.Lock()

    @property
    def source(self) -> Source:
        return self._source

    async def fetch(self) -> SupplierPackage:
        headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._http_timeout),
            headers=headers,
            follow_redirects=True,
            transport=self._transport,
        ) as http:
            firm_rubrics, price_rubrics = await self._rubrics(http)
            companies: dict[str, parsing.ListedCompany] = {}
            for rubric in firm_rubrics:
                async for tree in self._pages(http, rubric):
                    for company in parsing.companies(tree):
                        companies.setdefault(company.company_id, company)
            listed: dict[str, parsing.ListedProduct] = {}
            for rubric in price_rubrics:
                async for tree in self._pages(http, rubric):
                    for product in parsing.products(tree):
                        listed.setdefault(product.external_id, product)
            sellers: dict[str, parsing.ProductSeller | None] = {}
            for product in listed.values():
                sellers[product.external_id] = await self._seller(http, product)
        if not companies and not listed:
            raise SourceUnavailableError(f"{self._sitemap_url}: рубрики не содержат данных")
        logger.info("Пульс цен: компаний — %d, товаров — %d", len(companies), len(listed))
        suppliers = {
            company.company_id: self._builder.supplier(company) for company in companies.values()
        }
        for seller in sellers.values():
            if seller is not None and seller.company_id not in suppliers:
                suppliers[seller.company_id] = self._builder.seller_supplier(seller)
        return SupplierPackage(
            source=self._source,
            suppliers=tuple(suppliers.values()),
            offers=tuple(
                self._builder.offer(product, sellers[product.external_id])
                for product in listed.values()
            ),
        )

    async def _seller(
        self, http: httpx.AsyncClient, product: parsing.ListedProduct
    ) -> parsing.ProductSeller | None:
        text = await self._get(http, product.url)
        tree = await asyncio.to_thread(page.parse, text, product.url)
        seller = parsing.product_seller(tree)
        if seller is None:
            logger.warning("В карточке %s не найден продавец", product.url)
        return seller

    async def _rubrics(self, http: httpx.AsyncClient) -> tuple[list[str], list[str]]:
        async def read(url: str) -> bytes:
            await self._wait_turn()
            response = await http.get(url)
            if parsing.is_bot_check(response.text):
                raise BotProtectionError(f"{url}: сайт требует проверку на робота")
            response.raise_for_status()
            return response.content

        urls = await sitemaps.read_tree(read, self._sitemap_url, _wanted_sitemap)
        firms: list[str] = []
        prices: list[str] = []
        for url in dict.fromkeys(urls):
            path = urlsplit(url).path
            if "/f:" in path:
                continue
            if path.startswith(FIRMS_PREFIX):
                firms.append(url)
            elif path.startswith(PRICE_PREFIX):
                prices.append(url)
        if not firms and not prices:
            raise SourceUnavailableError(f"{self._sitemap_url}: в sitemap нет рубрик")
        return firms, prices

    async def _pages(self, http: httpx.AsyncClient, rubric: str):
        seen: set[str] = set()
        number = 1
        while True:
            url = rubric if number == 1 else f"{rubric}?page={number}"
            text = await self._get(http, url)
            tree = await asyncio.to_thread(page.parse, text, url)
            marker = page.document_text(tree)[:2000]
            if marker in seen:
                raise SourceUnavailableError(f"{url}: пагинация зациклилась")
            seen.add(marker)
            yield tree
            if not parsing.has_next_page(tree):
                return
            number += 1

    async def _get(self, http: httpx.AsyncClient, url: str) -> str:
        await self._wait_turn()
        try:
            response = await http.get(url)
        except httpx.HTTPError as error:
            raise SourceUnavailableError(f"{url}: {error}") from error
        if parsing.is_bot_check(response.text):
            raise BotProtectionError(f"{url}: сайт требует проверку на робота")
        if response.status_code >= 400:
            raise SourceUnavailableError(f"{url}: HTTP {response.status_code}")
        return response.text

    async def _wait_turn(self) -> None:
        async with self._pace:
            pause = self._next_request_at - time.monotonic()
            if pause > 0:
                await asyncio.sleep(pause)
            self._next_request_at = time.monotonic() + self._delay
