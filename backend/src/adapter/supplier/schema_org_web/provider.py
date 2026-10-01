"""Адаптер сайта поставщика: sitemap.xml и разметка schema.org.

Карточки с разметкой `Product` и `Offer` в JSON-LD дают товарные поля без
догадок о вёрстке. Адреса берутся из sitemap, поэтому обход не зависит от
структуры навигации. Извлекаются только фактически присутствующие поля.

Страницы читаются одновременно, число запросов к сайту ограничено семафором.
Недоступная карточка пропускается и не отменяет остальные.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from src.adapter.supplier import identity, jsonld, page, sitemap
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
        for url, read in zip(urls, pages, strict=True):
            if isinstance(read, BaseException):
                # Одна недоступная карточка не отменяет обход остальных.
                logger.warning("Страница %s не прочитана: %s", url, read)
                continue
            text, found = read
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
        urls = await sitemap.read_urls(http, self._sitemap_url)
        if self._url_pattern:
            urls = [url for url in urls if self._url_pattern in url]
        if not urls:
            raise SourceUnavailableError(f"{self._sitemap_url}: в sitemap нет подходящих адресов")
        return urls[: self._max_pages]

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
        offer_data = jsonld.first(product.get("offers"))
        url = jsonld.text(offer_data.get("url")) or jsonld.text(product.get("url")) or page_url
        sku = jsonld.text(product.get("sku")) or jsonld.text(offer_data.get("sku"))
        external_id = jsonld.text(product.get("productID")) or sku or url
        item_type = ItemType.SERVICE if "Service" in jsonld.type_names(product) else ItemType.GOODS
        name = jsonld.text(product.get("name"))
        description = jsonld.text(product.get("description"))
        brand = jsonld.text(jsonld.first(product.get("brand")).get("name") or product.get("brand"))
        article = jsonld.text(product.get("mpn")) or sku
        attributes = _attributes(product)
        unit = jsonld.text(product.get("unitText"))
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
            source_category=jsonld.text(product.get("category")),
            price=jsonld.number(offer_data.get("price")),
            currency=jsonld.text(offer_data.get("priceCurrency")),
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


def _read_page(text: str, url: str) -> tuple[str, list[dict[str, Any]]]:
    """Разбор HTML блокирующий: вызывается в пуле потоков."""
    tree = page.parse(text, url)
    products = jsonld.of_types(jsonld.nodes(tree), jsonld.PRODUCT_TYPES)
    return page.document_text(tree), products


def _attributes(product: dict[str, Any]) -> dict[str, str]:
    attributes: dict[str, str] = {}
    properties = product.get("additionalProperty")
    items = properties if isinstance(properties, list) else [properties]
    for item in items:
        if not isinstance(item, dict):
            continue
        name = jsonld.text(item.get("name"))
        value = jsonld.text(item.get("value"))
        if name and value:
            attributes[name] = value
    for key in ("color", "material", "size", "weight", "gtin13"):
        value = jsonld.text(product.get(key))
        if value:
            attributes[key] = value
    return attributes


def _availability(raw: Any) -> Availability:
    value = jsonld.text(raw).rsplit("/", 1)[-1].casefold()
    return _AVAILABILITY.get(value, Availability.UNKNOWN)
