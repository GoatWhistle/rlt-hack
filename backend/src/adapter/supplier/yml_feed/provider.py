"""Адаптер YML-фида магазина поставщика.

Фид — самый надёжный источник ассортимента: предложения представлены
элементами `offer` с идентификаторами и товарными полями. Один фид описывает
каталог целиком, поэтому пакет содержит весь ассортимент магазина, а исчезнувшие
из фида предложения хранилище снимает с продажи.
"""

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

import httpx

from src.adapter.supplier import identity
from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.inn import normalize_inn
from src.models.enums import Availability, ItemType, SupplierRole
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier

logger = logging.getLogger(__name__)

PROVIDER_NAME = "yml_feed"

# Значение заголовка обязано быть ASCII: контакт указывается при развёртывании.
USER_AGENT = "rlt-supplier-search/0.1 (+contact: see deployment configuration)"

MAX_FEED_BYTES = 32 * 1024 * 1024


class YmlFeedProvider:
    """Читает один фид магазина по его адресу."""

    def __init__(
        self,
        source_defaults: Source,
        feed_url: str = "",
        supplier_inn: str = "",
        delivery_regions: tuple[str, ...] = (),
        supplier_role: SupplierRole = SupplierRole.UNKNOWN,
        http_timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._source = source_defaults
        self._feed_url = feed_url or source_defaults.base_url
        self._supplier_inn = supplier_inn
        self._delivery_regions = delivery_regions
        self._supplier_role = supplier_role
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
            try:
                response = await http.get(self._feed_url)
                response.raise_for_status()
            except httpx.HTTPError as error:
                raise SourceUnavailableError(f"{self._feed_url}: {error}") from error
            content = response.content
        if len(content) > MAX_FEED_BYTES:
            raise SourceUnavailableError(
                f"{self._feed_url}: фид больше {MAX_FEED_BYTES} байт и не обработан"
            )
        # Разбор больших фидов блокирует событийный цикл: он идёт в пуле потоков.
        root = await asyncio.to_thread(self._parse, content)
        shop = self._shop(root)
        supplier = self._supplier(shop)
        offers = tuple(self._offers(shop, supplier))
        logger.info("Фид %s: предложений — %d", self._feed_url, len(offers))
        return SupplierPackage(source=self._source, suppliers=(supplier,), offers=offers)

    def _parse(self, content: bytes) -> ElementTree.Element:
        try:
            return ElementTree.fromstring(content)
        except ElementTree.ParseError as error:
            raise ContentFormatError(f"{self._feed_url}: XML не разобран: {error}") from error

    def _shop(self, root: ElementTree.Element) -> ElementTree.Element:
        """Возвращает раздел shop: часть выгрузок отдаёт его корневым элементом."""
        shop = root.find("shop")
        if shop is None and root.find("offers") is not None:
            shop = root
        if shop is None:
            raise ContentFormatError(f"{self._feed_url}: в фиде нет раздела shop с предложениями")
        return shop

    def _supplier(self, shop: ElementTree.Element) -> Supplier:
        """Владелец фида. Принадлежность подтверждается на уровне источника."""
        inn = normalize_inn(self._supplier_inn)
        return Supplier(
            supplier_id=self._source.supplier_id
            or identity.supplier_id(inn, self._source.source_id, "self"),
            name=_text(shop, "company") or _text(shop, "name") or self._source.name,
            inn=inn,
            website=_text(shop, "url") or self._source.base_url,
            identity_status=self._source.ownership_status,
            identity_evidence_url=self._source.ownership_evidence_url,
        )

    def _offers(self, shop: ElementTree.Element, supplier: Supplier) -> list[Offer]:
        categories = {
            element.get("id", ""): (element.text or "").strip()
            for element in shop.iterfind("categories/category")
        }
        observed_at = datetime.now(UTC)
        offers: list[Offer] = []
        for element in shop.iterfind("offers/offer"):
            url = _text(element, "url")
            external_id = element.get("id") or url
            if not external_id:
                # Без устойчивого ключа предложение нельзя обновлять повторно.
                continue
            name = _name(element)
            description = _text(element, "description")
            brand = _text(element, "vendor")
            article = _text(element, "vendorCode")
            attributes = _attributes(element)
            unit = _text(element, "unit")
            offers.append(
                Offer(
                    offer_id=identity.offer_id(self._source.source_id, external_id),
                    source_id=self._source.source_id,
                    external_id=external_id,
                    url=url or self._source.base_url,
                    name=name,
                    first_seen_at=observed_at,
                    last_seen_at=observed_at,
                    supplier_id=supplier.supplier_id,
                    seller_status=self._source.ownership_status,
                    seller_evidence_url=self._source.ownership_evidence_url,
                    description=description,
                    item_type=ItemType.GOODS,
                    brand=brand,
                    article=article,
                    attributes=attributes,
                    source_category=categories.get(_text(element, "categoryId"), ""),
                    price=_decimal(_text(element, "price")),
                    currency=_text(element, "currencyId"),
                    unit=unit,
                    # Фид редко указывает географию: регионы берутся из настроек источника.
                    delivery_regions=self._delivery_regions,
                    availability=_availability(element),
                    supplier_role=self._supplier_role,
                    content_hash=identity.offer_content_hash(
                        name=name,
                        description=description,
                        item_type=str(ItemType.GOODS),
                        brand=brand,
                        article=article,
                        unit=unit,
                        attributes=attributes,
                    ),
                )
            )
        return offers


def _text(element: ElementTree.Element, path: str) -> str:
    found = element.find(path)
    if found is None or found.text is None:
        return ""
    return " ".join(found.text.split())


def _name(element: ElementTree.Element) -> str:
    direct = _text(element, "name")
    if direct:
        return direct
    parts = (_text(element, "typePrefix"), _text(element, "vendor"), _text(element, "model"))
    return " ".join(part for part in parts if part)


def _attributes(element: ElementTree.Element) -> dict[str, str]:
    attributes = {
        param.get("name", ""): " ".join((param.text or "").split())
        for param in element.iterfind("param")
        if param.get("name")
    }
    sales_notes = _text(element, "sales_notes")
    if sales_notes:
        attributes["sales_notes"] = sales_notes
    return attributes


def _availability(element: ElementTree.Element) -> Availability:
    """`available="false"` в YML означает поставку под заказ, а не отсутствие."""
    raw = element.get("available")
    if raw is None:
        return Availability.UNKNOWN
    return Availability.AVAILABLE if raw.lower() == "true" else Availability.ON_ORDER


def _decimal(raw: str) -> Decimal | None:
    if not raw:
        return None
    try:
        value = Decimal(raw.replace(",", ".").replace(" ", ""))
    except InvalidOperation:
        return None
    return value if value >= 0 else None
