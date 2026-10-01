"""Адаптер каталога производителей ТехЗаказ (texzakaz.ru).

Адреса карточек берутся из `sitemap.xml`: это перечень, который источник ведёт
сам, поэтому обход не зависит от пагинации списка `/proizvoditeli`. Раздел
`/api/` закрыт в `robots.txt`, поэтому машинным интерфейсом служат sitemap и
разметка карточки.

Карточка компании размечена JSON-LD: `Organization` даёт название, юридическое
наименование, ИНН и регион, а `knowsAbout` — перечень выпускаемой продукции.
Позиции `knowsAbout` сохраняются предложениями без цены: каталог публикует
номенклатуру, а не прайс.
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
from src.models.enums import ItemType, SupplierRole, VerificationStatus
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier

logger = logging.getLogger(__name__)

PROVIDER_NAME = "texzakaz_web"

BASE_URL = "https://texzakaz.ru/"

SITEMAP_URL = "https://texzakaz.ru/sitemap.xml"

# Карточки производителей лежат в разделе `/p/`: он разрешён в robots.txt.
CARD_PREFIX = "/p/"

# Значение заголовка обязано быть ASCII: контакт указывается при развёртывании.
USER_AGENT = "rlt-supplier-search/0.1 (+contact: see deployment configuration)"


class TexZakazWebProvider:
    """Обходит карточки производителей из sitemap и собирает их разметку."""

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
                # Одна недоступная карточка не отменяет обход остальных.
                logger.warning("Карточка производителя %s не прочитана: %s", url, card)
                continue
            supplier, products = card
            if supplier is None:
                continue
            suppliers[str(supplier.supplier_id)] = supplier
            offers.extend(products)
        logger.info(
            "ТехЗаказ: карточек — %d, компаний — %d, позиций — %d",
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
        urls = [
            url
            for url in await sitemap.read_urls(http, self._sitemap_url)
            if urlsplit(url).path.startswith(CARD_PREFIX)
        ]
        if not urls:
            raise SourceUnavailableError(
                f"{self._sitemap_url}: в sitemap нет карточек производителей"
            )
        return urls[: self._max_companies]

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
        organization = jsonld.first_of_types(jsonld.nodes(tree), jsonld.ORGANIZATION_TYPES)
        supplier = self._supplier(tree, organization, url)
        if supplier is None:
            logger.warning("Карточка %s пропущена: на странице нет компании", url)
            return None, ()
        products = jsonld.strings(organization.get("knowsAbout"))
        return supplier, tuple(self._offer(name, url, supplier) for name in products)

    def _supplier(self, tree: Any, organization: dict[str, Any], url: str) -> Supplier | None:
        name = jsonld.text(organization.get("name")) or page.first_text(tree, "h1")
        if not name:
            return None
        document = page.document_text(tree)
        inn = normalize_inn(jsonld.text(organization.get("taxID"))) or find_inn(document)
        address = jsonld.first(organization.get("address"))
        region = jsonld.text(address.get("addressRegion"))
        locality = jsonld.text(address.get("addressLocality"))
        kpp = find_kpp(document)
        contacts = {
            key: value
            for key, value in (
                ("legal_name", jsonld.text(organization.get("alternateName"))),
                ("locality", locality),
                ("phone", jsonld.text(organization.get("telephone"))),
                ("email", jsonld.text(organization.get("email"))),
            )
            if value
        }
        return Supplier(
            supplier_id=identity.supplier_id(inn, self._source.source_id, url),
            name=name,
            inn=inn,
            kpps=(kpp,) if kpp else (),
            region=region or locality,
            website=page.external_link(tree, "a[href^='http']", self._source.base_url),
            contacts=contacts,
            # Каталог не подтверждает реквизиты: статус проверяет отдельная джоба.
            identity_status=VerificationStatus.UNVERIFIED,
            identity_evidence_url=url,
        )

    def _offer(self, name: str, url: str, supplier: Supplier) -> Offer:
        external_id = f"{url}#{name}"
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
            seller_status=VerificationStatus.UNVERIFIED,
            seller_evidence_url=url,
            item_type=ItemType.GOODS,
            # Каталог ведёт реестр производителей: роль объявлена разделом источника.
            supplier_role=SupplierRole.MANUFACTURER,
            role_evidence_url=url,
            content_hash=identity.offer_content_hash(name=name, item_type=str(ItemType.GOODS)),
        )
