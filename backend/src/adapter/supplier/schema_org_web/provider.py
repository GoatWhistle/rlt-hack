"""Адаптер сайта поставщика: sitemap.xml и разметка schema.org.

Карточки с разметкой `Product` и `Offer` в JSON-LD дают товарные поля без
догадок о вёрстке. Адреса берутся из sitemap, поэтому обход не зависит от
структуры навигации. Извлекаются только фактически присутствующие поля.

Страницы читаются одновременно, число запросов к сайту ограничено семафором.
Недоступная карточка пропускается и не отменяет остальные.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from xml.etree import ElementTree

import httpx
from lxml import html as lxml_html

from src.adapter.supplier import identity
from src.adapter.supplier.errors import SourceUnavailableError
from src.adapter.supplier.inn import find_inn, find_kpp, normalize_inn
from src.models.enums import Availability, ItemType, SupplierRole
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier

logger = logging.getLogger(__name__)

PROVIDER_NAME = "schema_org_web"

# Значение заголовка обязано быть ASCII: контакт указывается при развёртывании.
USER_AGENT = "rlt-supplier-search/0.1 (+contact: see deployment configuration)"

MAX_SITEMAP_DEPTH = 2

_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

_PRODUCT_TYPES = {"Product", "IndividualProduct", "ProductModel", "Service"}

_AVAILABILITY = {
    "instock": Availability.AVAILABLE,
    "limitedavailability": Availability.AVAILABLE,
    "onlineonly": Availability.AVAILABLE,
    "outofstock": Availability.UNAVAILABLE,
    "soldout": Availability.UNAVAILABLE,
    "discontinued": Availability.UNAVAILABLE,
    "preorder": Availability.ON_ORDER,
    "backorder": Availability.ON_ORDER,
    "presale": Availability.ON_ORDER,
}


class SchemaOrgWebProvider:
    """Обходит адреса из sitemap и читает Product/Offer со страниц сайта."""

    def __init__(
        self,
        source_defaults: Source,
        sitemap_url: str = "",
        url_pattern: str = "",
        supplier_inn: str = "",
        max_pages: int = 200,
        max_concurrent: int = 4,
        http_timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._source = source_defaults
        self._sitemap_url = sitemap_url or source_defaults.base_url.rstrip("/") + "/sitemap.xml"
        self._url_pattern = url_pattern
        self._supplier_inn = supplier_inn
        self._max_pages = max_pages
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
            urls = await self._page_urls(http)
            limit = asyncio.Semaphore(self._max_concurrent)
            pages = await asyncio.gather(
                *(self._page(http, url, limit) for url in urls),
                return_exceptions=True,
            )
        products: list[tuple[str, dict[str, Any]]] = []
        page_texts: list[str] = []
        for url, page in zip(urls, pages, strict=True):
            if isinstance(page, BaseException):
                # Одна недоступная карточка не отменяет обход остальных.
                logger.warning("Страница %s не прочитана: %s", url, page)
                continue
            text, found = page
            page_texts.append(text)
            products.extend((url, product) for product in found)
        supplier = self._supplier(page_texts)
        offers = tuple(self._offer(product, url, supplier) for url, product in products)
        logger.info(
            "Сайт %s: страниц — %d, предложений — %d",
            self._source.base_url,
            len(urls),
            len(offers),
        )
        return SupplierPackage(source=self._source, suppliers=(supplier,), offers=offers)

    async def _page_urls(self, http: httpx.AsyncClient) -> list[str]:
        urls = await self._read_sitemap(http, self._sitemap_url, depth=0)
        if self._url_pattern:
            urls = [url for url in urls if self._url_pattern in url]
        if not urls:
            raise SourceUnavailableError(f"{self._sitemap_url}: в sitemap нет подходящих адресов")
        return urls[: self._max_pages]

    async def _read_sitemap(self, http: httpx.AsyncClient, url: str, depth: int) -> list[str]:
        if depth > MAX_SITEMAP_DEPTH:
            # Глубже обычного вложения индексов не идём.
            return []
        try:
            response = await http.get(url)
            response.raise_for_status()
        except httpx.HTTPError as error:
            if depth == 0:
                raise SourceUnavailableError(f"{url}: {error}") from error
            logger.warning("Вложенный sitemap %s не прочитан: %s", url, error)
            return []
        root = await asyncio.to_thread(_parse_xml, response.content, url)
        urls = [
            element.text.strip()
            for element in root.findall("sm:url/sm:loc", _SITEMAP_NS)
            if element.text
        ]
        for nested in root.findall("sm:sitemap/sm:loc", _SITEMAP_NS):
            if nested.text:
                urls.extend(await self._read_sitemap(http, nested.text.strip(), depth + 1))
        return urls

    async def _page(
        self,
        http: httpx.AsyncClient,
        url: str,
        limit: asyncio.Semaphore,
    ) -> tuple[str, list[dict[str, Any]]]:
        async with limit:
            response = await http.get(url)
            response.raise_for_status()
        return await asyncio.to_thread(_read_page, response.text, str(response.url))

    def _supplier(self, page_texts: list[str]) -> Supplier:
        """Реквизиты из текста страниц: совпадение названия продавцом не считается."""
        inn = normalize_inn(self._supplier_inn)
        kpp = None
        for text in page_texts:
            inn = inn or find_inn(text)
            kpp = kpp or find_kpp(text)
            if inn and kpp:
                break
        return Supplier(
            supplier_id=self._source.supplier_id
            or identity.supplier_id(inn, self._source.source_id, "self"),
            name=self._source.name,
            inn=inn,
            kpps=(kpp,) if kpp else (),
            website=self._source.base_url,
            identity_status=self._source.ownership_status,
            identity_evidence_url=self._source.ownership_evidence_url or self._source.base_url,
        )

    def _offer(self, product: dict[str, Any], page_url: str, supplier: Supplier) -> Offer:
        offer_data = _first(product.get("offers"))
        url = _text(offer_data.get("url")) or _text(product.get("url")) or page_url
        sku = _text(product.get("sku")) or _text(offer_data.get("sku"))
        external_id = _text(product.get("productID")) or sku or url
        item_type = ItemType.SERVICE if "Service" in _type_names(product) else ItemType.GOODS
        name = _text(product.get("name"))
        description = _text(product.get("description"))
        brand = _text(_first(product.get("brand")).get("name") or product.get("brand"))
        article = _text(product.get("mpn")) or sku
        attributes = _attributes(product)
        unit = _text(product.get("unitText"))
        observed_at = datetime.now(UTC)
        return Offer(
            offer_id=identity.offer_id(self._source.source_id, external_id),
            source_id=self._source.source_id,
            external_id=external_id,
            url=url,
            name=name,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
            supplier_id=supplier.supplier_id,
            seller_status=self._source.ownership_status,
            seller_evidence_url=self._source.ownership_evidence_url or self._source.base_url,
            description=description,
            item_type=item_type,
            brand=brand,
            article=article,
            attributes=attributes,
            source_category=_text(product.get("category")),
            price=_decimal(offer_data.get("price")),
            currency=_text(offer_data.get("priceCurrency")),
            unit=unit,
            availability=_availability(offer_data.get("availability")),
            # Сайт компании подтверждает продавца, но не роль в поставке товара.
            supplier_role=SupplierRole.UNKNOWN,
            role_evidence_url=page_url,
            content_hash=identity.offer_content_hash(
                name=name,
                description=description,
                item_type=str(item_type),
                brand=brand,
                article=article,
                unit=unit,
                attributes=attributes,
            ),
        )


def _parse_xml(content: bytes, url: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise SourceUnavailableError(f"{url}: XML не разобран: {error}") from error


def _read_page(text: str, url: str) -> tuple[str, list[dict[str, Any]]]:
    """Разбор HTML блокирующий: вызывается в пуле потоков.

    Кодировку задаёт ответ сервера: иначе lxml читает кириллицу как latin-1.
    """
    parser = lxml_html.HTMLParser(encoding="utf-8")
    tree = lxml_html.fromstring(text.encode("utf-8"), base_url=url, parser=parser)
    products: list[dict[str, Any]] = []
    for script in tree.iter("script"):
        if (script.get("type") or "").strip().lower() != "application/ld+json":
            continue
        raw = (script.text_content() or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except ValueError:
            # Некорректный JSON-LD пропускаем: страница может быть валидной в остальном.
            continue
        products.extend(_collect_products(payload))
    return " ".join(tree.text_content().split()), products


def _collect_products(payload: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            found.extend(_collect_products(item))
        return found
    if not isinstance(payload, dict):
        return found
    if "@graph" in payload:
        found.extend(_collect_products(payload["@graph"]))
    if _PRODUCT_TYPES & _type_names(payload):
        found.append(payload)
    return found


def _type_names(payload: dict[str, Any]) -> set[str]:
    types = payload.get("@type", "")
    return {types} if isinstance(types, str) else set(types or ())


def _attributes(product: dict[str, Any]) -> dict[str, str]:
    attributes: dict[str, str] = {}
    properties = product.get("additionalProperty")
    items = properties if isinstance(properties, list) else [properties]
    for item in items:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"))
        value = _text(item.get("value"))
        if name and value:
            attributes[name] = value
    for key in ("color", "material", "size", "weight", "gtin13"):
        value = _text(product.get(key))
        if value:
            attributes[key] = value
    return attributes


def _availability(raw: Any) -> Availability:
    value = _text(raw).rsplit("/", 1)[-1].casefold()
    return _AVAILABILITY.get(value, Availability.UNKNOWN)


def _first(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
        return {}
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    if value is None or isinstance(value, (dict, list)):
        return ""
    return " ".join(str(value).split())


def _decimal(value: Any) -> Decimal | None:
    text = _text(value).replace(",", ".").replace(" ", "")
    if not text:
        return None
    try:
        price = Decimal(text)
    except InvalidOperation:
        return None
    return price if price >= 0 else None
