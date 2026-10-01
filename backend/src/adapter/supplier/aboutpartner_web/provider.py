"""Адаптер каталога компаний «О Партнёре» (aboutpartner.ru).

Цепочка обхода: раздел `/catalog` → страницы разделов → карточки компаний
`/company` → реквизиты компании. Разделы и селекторы заданы в адаптере.

Ассортимент каталога не разбирается: разметка карточек товаров не сверена с
живыми страницами, поэтому пакет содержит только компании.
"""

import asyncio
import logging
from typing import Any
from urllib.parse import urlsplit

import httpx
from lxml import html as lxml_html

from src.adapter.supplier import identity
from src.adapter.supplier.errors import SourceUnavailableError
from src.adapter.supplier.inn import find_inn, find_kpp
from src.models.enums import VerificationStatus
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier

logger = logging.getLogger(__name__)

PROVIDER_NAME = "aboutpartner_web"

BASE_URL = "https://aboutpartner.ru/"

CATALOG_URL = "https://aboutpartner.ru/catalog/"

# Значение заголовка обязано быть ASCII: контакт указывается при развёртывании.
USER_AGENT = "rlt-supplier-search/0.1 (+contact: see deployment configuration)"

_SECTION_LINKS = "a[href*='/catalog/']"
_COMPANY_LINKS = "a[href*='/company']"
_NEXT_PAGE = "a.next, a[rel='next'], .pagination a[href*='page']"
_COMPANY_NAME = "h1"
_COMPANY_REGION = ".city, .region, .company-city"


class AboutPartnerWebProvider:
    """Обходит разделы каталога «О Партнёре» и собирает компании."""

    def __init__(
        self,
        source_defaults: Source,
        catalog_url: str = CATALOG_URL,
        max_sections: int = 20,
        max_pages_per_section: int = 5,
        max_companies: int = 500,
        max_concurrent: int = 4,
        http_timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._source = source_defaults
        self._catalog_url = catalog_url
        self._max_sections = max_sections
        self._max_pages_per_section = max_pages_per_section
        self._max_companies = max_companies
        self._max_concurrent = max(1, max_concurrent)
        self._http_timeout = http_timeout
        self._transport = transport

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
            sections = await self._sections(http)
            company_urls = await self._company_urls(http, sections)
            limit = asyncio.Semaphore(self._max_concurrent)
            cards = await asyncio.gather(
                *(self._company(http, url, limit) for url in company_urls),
                return_exceptions=True,
            )
        suppliers: dict[str, Supplier] = {}
        for url, supplier in zip(company_urls, cards, strict=True):
            if isinstance(supplier, BaseException):
                logger.warning("Карточка компании %s не прочитана: %s", url, supplier)
                continue
            suppliers[str(supplier.supplier_id)] = supplier
        logger.info(
            "О Партнёре: разделов — %d, карточек — %d, компаний — %d",
            len(sections),
            len(company_urls),
            len(suppliers),
        )
        return SupplierPackage(source=self._source, suppliers=tuple(suppliers.values()))

    async def _sections(self, http: httpx.AsyncClient) -> list[str]:
        """Со страницы каталога берутся разделы; сама страница тоже обходится."""
        tree = await self._page(http, self._catalog_url)
        sections = [self._catalog_url]
        for url in _links(tree, _SECTION_LINKS):
            if url not in sections:
                sections.append(url)
        if len(sections) == 1 and not _links(tree, _COMPANY_LINKS):
            raise SourceUnavailableError(
                f"{self._catalog_url}: на странице каталога нет ни разделов, ни компаний"
            )
        return sections[: self._max_sections]

    async def _company_urls(self, http: httpx.AsyncClient, sections: list[str]) -> list[str]:
        found: list[str] = []
        for section in sections:
            page_url = section
            for _ in range(self._max_pages_per_section):
                try:
                    tree = await self._page(http, page_url)
                except httpx.HTTPError as error:
                    logger.warning("Страница раздела %s не прочитана: %s", page_url, error)
                    break
                for url in _links(tree, _COMPANY_LINKS):
                    if url not in found:
                        found.append(url)
                if len(found) >= self._max_companies:
                    return found[: self._max_companies]
                next_page = _first_link(tree, _NEXT_PAGE)
                if not next_page or next_page == page_url:
                    break
                page_url = next_page
        return found[: self._max_companies]

    async def _company(
        self,
        http: httpx.AsyncClient,
        url: str,
        limit: asyncio.Semaphore,
    ) -> Supplier:
        async with limit:
            tree = await self._page(http, url)
        page_text = _document_text(tree)
        inn = find_inn(page_text)
        kpp = find_kpp(page_text)
        return Supplier(
            supplier_id=identity.supplier_id(inn, self._source.source_id, url),
            name=_first_text(tree, _COMPANY_NAME) or self._source.name,
            inn=inn,
            kpps=(kpp,) if kpp else (),
            region=_first_text(tree, _COMPANY_REGION),
            website=_external_link(tree, self._source.base_url),
            identity_status=VerificationStatus.UNVERIFIED,
            identity_evidence_url=url,
        )

    async def _page(self, http: httpx.AsyncClient, url: str) -> Any:
        response = await http.get(url)
        response.raise_for_status()
        return await asyncio.to_thread(_parse_html, response.text, str(response.url))


def _parse_html(text: str, url: str) -> Any:
    """Кодировку задаёт ответ сервера: иначе lxml читает кириллицу как latin-1."""
    parser = lxml_html.HTMLParser(encoding="utf-8")
    tree = lxml_html.fromstring(text.encode("utf-8"), base_url=url, parser=parser)
    tree.make_links_absolute(url, resolve_base_href=True)
    return tree


def _links(tree: Any, selector: str) -> list[str]:
    found: list[str] = []
    for element in tree.cssselect(selector):
        href = element.get("href")
        if href and href not in found:
            found.append(href)
    return found


def _first_link(tree: Any, selector: str) -> str:
    links = _links(tree, selector)
    return links[0] if links else ""


def _first_text(tree: Any, selector: str) -> str:
    for element in tree.cssselect(selector):
        text = " ".join(element.text_content().split())
        if text:
            return text
    return ""


def _external_link(tree: Any, base_url: str) -> str:
    host = urlsplit(base_url).netloc
    for element in tree.cssselect("a[href^='http']"):
        href = element.get("href", "")
        if host not in urlsplit(href).netloc:
            return href
    return ""


def _document_text(tree: Any) -> str:
    for element in list(tree.iter("script", "style", "noscript")):
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)
    return " ".join(tree.text_content().split())
