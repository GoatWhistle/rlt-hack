"""Адаптер каталога компаний «О Партнёре» (aboutpartner.ru).

Адреса карточек берутся из `sitemap-producers.xml`, указанного в индексе
источника: перебор списка `/producers` закрыт в `robots.txt` параметром `?page=`,
как и раздел `/api/`. Поэтому машинным интерфейсом служат sitemap и разметка
карточки.

Карточка размечена JSON-LD: `Organization` даёт название, юридическое
наименование, ИНН, контакты и регион, а `ItemList` с узлами `Product` —
ассортимент компании. Страницы без `Organization` (карточки сервисов) в
результат не попадают.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from src.adapter.supplier import identity, jsonld, page, sitemap
from src.adapter.supplier.errors import SourceUnavailableError
from src.adapter.supplier.inn import find_inn, find_kpp, normalize_inn
from src.models.catalog.offer import Offer
from src.models.catalog.package import SupplierPackage
from src.models.catalog.source import Source
from src.models.catalog.supplier import Supplier
from src.models.enums import ItemType, SupplierRole, VerificationStatus

logger = logging.getLogger(__name__)

PROVIDER_NAME = "aboutpartner_web"

BASE_URL = "https://aboutpartner.ru/"

SITEMAP_URL = "https://aboutpartner.ru/sitemap-producers.xml"

# Карточки компаний лежат в разделе `/producer/`: он разрешён в robots.txt.
CARD_PREFIX = "/producer/"

# В том же разделе лежат карточки сервисов, и в sitemap они идут первыми. Карточки
# компаний узнаются по началу адреса и обходятся раньше, иначе короткий обход
# тратит все запросы на страницы без компании.
COMPANY_SLUG = "pc-producer-"

# Значение заголовка обязано быть ASCII: контакт указывается при развёртывании.
USER_AGENT = "rlt-supplier-search/0.1 (+contact: see deployment configuration)"


class AboutPartnerWebProvider:
    """Обходит карточки компаний из sitemap и собирает их разметку."""

    def __init__(
        self,
        source_defaults: Source,
        sitemap_url: str = SITEMAP_URL,
        max_companies: int = 500,
        max_concurrent: int = 4,
        http_timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._source = source_defaults
        self._sitemap_url = sitemap_url
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
            company_urls = await self._company_urls(http)
            limit = asyncio.Semaphore(self._max_concurrent)
            cards = await asyncio.gather(
                *(self._card(http, url, limit) for url in company_urls),
                return_exceptions=True,
            )
        suppliers: dict[str, Supplier] = {}
        offers: list[Offer] = []
        for url, card in zip(company_urls, cards, strict=True):
            if isinstance(card, BaseException):
                logger.warning("Карточка компании %s не прочитана: %s", url, card)
                continue
            supplier, products = card
            if supplier is None:
                continue
            suppliers[str(supplier.supplier_id)] = supplier
            offers.extend(products)
        logger.info(
            "О Партнёре: карточек — %d, компаний — %d, предложений — %d",
            len(company_urls),
            len(suppliers),
            len(offers),
        )
        return SupplierPackage(
            source=self._source,
            suppliers=tuple(suppliers.values()),
            offers=tuple(offers),
        )

    async def _company_urls(self, http: httpx.AsyncClient) -> list[str]:
        cards = [
            url
            for url in await sitemap.read_urls(http, self._sitemap_url)
            if urlsplit(url).path.startswith(CARD_PREFIX)
        ]
        if not cards:
            raise SourceUnavailableError(f"{self._sitemap_url}: в sitemap нет карточек компаний")
        companies = [url for url in cards if COMPANY_SLUG in urlsplit(url).path]
        others = [url for url in cards if COMPANY_SLUG not in urlsplit(url).path]
        return (companies + others)[: self._max_companies]

    async def _card(
        self,
        http: httpx.AsyncClient,
        url: str,
        limit: asyncio.Semaphore,
    ) -> tuple[Supplier | None, tuple[Offer, ...]]:
        async with limit:
            response = await http.get(url)
            response.raise_for_status()
        tree = await asyncio.to_thread(page.parse, response.text, str(response.url))
        nodes = jsonld.nodes(tree)
        organization = jsonld.first_of_types(nodes, jsonld.ORGANIZATION_TYPES)
        if not organization:
            # Раздел сервисов размечен SoftwareApplication: компании там нет.
            return None, ()
        supplier = self._supplier(tree, organization, url)
        products = [
            product
            for node in jsonld.of_types(nodes, frozenset({"ItemList"}))
            for product in _list_items(node)
        ]
        return supplier, tuple(self._offer(product, url, supplier) for product in products)

    def _supplier(self, tree: Any, organization: dict[str, Any], url: str) -> Supplier:
        document = page.document_text(tree)
        inn = normalize_inn(jsonld.text(organization.get("taxID"))) or find_inn(document)
        kpp = find_kpp(document)
        address = jsonld.first(organization.get("address"))
        region = jsonld.text(address.get("addressRegion"))
        locality = jsonld.text(address.get("addressLocality"))
        contacts = {
            key: value
            for key, value in (
                ("legal_name", jsonld.text(organization.get("legalName"))),
                ("phone", jsonld.text(organization.get("telephone"))),
                ("email", jsonld.text(organization.get("email"))),
                ("address", jsonld.text(address.get("streetAddress"))),
            )
            if value
        }
        return Supplier(
            supplier_id=identity.supplier_id(inn, self._source.source_id, url),
            name=jsonld.text(organization.get("name")) or page.first_text(tree, "h1"),
            inn=inn,
            kpps=(kpp,) if kpp else (),
            region=region or locality,
            website=_company_site(
                jsonld.strings(organization.get("sameAs")), self._source.base_url
            ),
            contacts=contacts,
            # Каталог не подтверждает реквизиты: статус проверяет отдельная джоба.
            identity_status=VerificationStatus.UNVERIFIED,
            identity_evidence_url=url,
        )

    def _offer(self, product: dict[str, Any], card_url: str, supplier: Supplier) -> Offer:
        name = jsonld.text(product.get("name"))
        url = jsonld.text(product.get("url")) or card_url
        description = jsonld.text(product.get("description"))
        brand = jsonld.text(jsonld.first(product.get("brand")).get("name") or product.get("brand"))
        item_type = ItemType.SERVICE if "Service" in jsonld.type_names(product) else ItemType.GOODS
        observed_at = datetime.now(UTC)
        external_id = identity.external_id(url=url)
        return Offer(
            offer_id=identity.offer_id(self._source.source_id, external_id),
            source_id=self._source.source_id,
            external_id=external_id,
            url=url,
            name=name,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
            supplier_id=supplier.supplier_id,
            seller_status=VerificationStatus.UNVERIFIED,
            evidence_url=card_url,
            description=description,
            item_type=item_type,
            brand=brand,
            # Каталог ведёт реестр производителей: роль объявлена разделом источника.
            supplier_role=SupplierRole.MANUFACTURER,
            content_hash=identity.offer_content_hash(
                name=name,
                description=description,
                item_type=str(item_type),
                brand=brand,
            ),
        )


def _list_items(node: dict[str, Any]) -> list[dict[str, Any]]:
    """Товары перечня: каждый элемент `ListItem` оборачивает узел `Product`."""
    elements = node.get("itemListElement")
    items = elements if isinstance(elements, list) else [elements]
    found: list[dict[str, Any]] = []
    for element in items:
        if not isinstance(element, dict):
            continue
        product = jsonld.first(element.get("item")) or element
        if jsonld.PRODUCT_TYPES & jsonld.type_names(product) and jsonld.text(product.get("name")):
            found.append(product)
    return found


def _company_site(addresses: tuple[str, ...], base_url: str) -> str:
    for address in addresses:
        if page.is_company_site(address, base_url):
            return address
    return ""
