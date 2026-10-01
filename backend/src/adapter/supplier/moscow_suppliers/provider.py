"""Чтение полного экспорта оферт и поставщиков Портала поставщиков Москвы.

Адрес экспорта задаётся явно: публичная документация портала описывает чтение
СТЕ, но не подтверждает интерфейс массового чтения оферт. Пакет не создаётся,
пока экспорт не содержит полного перечня оферт с продавцами и метаданных полноты.
"""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import httpx

from src.adapter.supplier import identity
from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.inn import normalize_inn
from src.models.enums import Availability, ItemType, VerificationStatus
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier

PROVIDER_NAME = "moscow_suppliers"
BASE_URL = "https://zakupki.mos.ru/"


class MoscowSuppliersProvider:
    def __init__(
        self,
        source_defaults: Source,
        export_url: str,
        http_timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._source = source_defaults
        self._export_url = export_url
        self._http_timeout = http_timeout
        self._transport = transport

    @property
    def source(self) -> Source:
        return self._source

    async def fetch(self) -> SupplierPackage:
        if not self._export_url:
            raise SourceUnavailableError("Не задан MOSCOW_SUPPLIERS_EXPORT_URL")
        suppliers: dict[str, Supplier] = {}
        offers: dict[str, Offer] = {}
        seen_pages: set[str] = set()
        expected_suppliers: int | None = None
        expected_offers: int | None = None
        snapshot_id: str | None = None
        next_url: str | None = self._export_url
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._http_timeout),
            follow_redirects=True,
            transport=self._transport,
        ) as http:
            while next_url is not None:
                if next_url in seen_pages:
                    raise ContentFormatError(f"Повтор страницы экспорта: {next_url}")
                seen_pages.add(next_url)
                try:
                    response = await http.get(next_url)
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    raise SourceUnavailableError(f"Экспорт недоступен: {next_url}") from exc
                try:
                    page = response.json()
                except ValueError as exc:
                    raise ContentFormatError(f"Экспорт не является JSON: {next_url}") from exc
                if not isinstance(page, dict) or page.get("complete") is not True:
                    raise ContentFormatError(f"Экспорт не подтверждает полный снимок: {next_url}")
                current_snapshot = _required(page, "snapshot_id")
                if snapshot_id is None:
                    snapshot_id = current_snapshot
                elif current_snapshot != snapshot_id:
                    raise ContentFormatError("Версия снимка изменилась во время обхода")
                totals = page.get("totals")
                if not isinstance(totals, dict):
                    raise ContentFormatError("Отсутствуют контрольные числа экспорта")
                supplier_total = _count(totals.get("suppliers"))
                offer_total = _count(totals.get("offers"))
                if expected_suppliers is None:
                    expected_suppliers, expected_offers = supplier_total, offer_total
                elif (supplier_total, offer_total) != (expected_suppliers, expected_offers):
                    raise ContentFormatError("Контрольные числа изменились во время обхода")
                rows_suppliers = page.get("suppliers")
                rows_offers = page.get("offers")
                if not isinstance(rows_suppliers, list) or not isinstance(rows_offers, list):
                    raise ContentFormatError("Нет массивов suppliers и offers")
                for row in rows_suppliers:
                    supplier = self._supplier(row)
                    key = _required(row, "id")
                    if key in suppliers:
                        raise ContentFormatError(f"Повтор поставщика: {key}")
                    suppliers[key] = supplier
                for row in rows_offers:
                    if not isinstance(row, dict):
                        raise ContentFormatError("Неверная запись оферты")
                    seller_key = _required(row, "supplier_id")
                    seller = suppliers.get(seller_key)
                    if seller is None:
                        raise ContentFormatError(
                            f"Поставщик {seller_key} отсутствует или идёт позже оферты"
                        )
                    offer = self._offer(row, seller)
                    key = offer.external_id
                    if key in offers:
                        raise ContentFormatError(f"Повтор оферты: {key}")
                    offers[key] = offer
                link = page.get("next")
                if link is not None and (not isinstance(link, str) or not link.strip()):
                    raise ContentFormatError("Неверная ссылка следующей страницы")
                next_url = urljoin(next_url, link) if link else None
        if len(suppliers) != expected_suppliers or len(offers) != expected_offers:
            raise ContentFormatError("Число уникальных записей не совпало с контрольным")
        if not suppliers or not offers:
            raise ContentFormatError("Пустой экспорт не подтверждает исчезновение оферт")
        return SupplierPackage(self._source, tuple(suppliers.values()), tuple(offers.values()))

    def _supplier(self, row: object) -> Supplier:
        if not isinstance(row, dict):
            raise ContentFormatError("Неверная запись поставщика")
        external_id = _required(row, "id")
        name = _required(row, "name")
        url = _required(row, "url")
        inn = normalize_inn(row.get("inn")) if row.get("inn") else None
        return Supplier(
            supplier_id=identity.supplier_id(inn, self._source.source_id, external_id),
            name=name,
            inn=inn,
            region=_optional(row, "region"),
            website=_optional(row, "website"),
            identity_status=VerificationStatus.UNVERIFIED,
            identity_evidence_url=url,
        )

    def _offer(self, row: object, seller: Supplier) -> Offer:
        if not isinstance(row, dict):
            raise ContentFormatError("Неверная запись оферты")
        external_id = _required(row, "id")
        sku_id = _required(row, "sku_id")
        name = _required(row, "name")
        url = _required(row, "url")
        price_raw = _required(row, "price")
        try:
            price = Decimal(price_raw)
        except InvalidOperation as exc:
            raise ContentFormatError(f"Неверная цена оферты {external_id}") from exc
        if not price.is_finite() or price < 0:
            raise ContentFormatError(f"Неверная цена оферты {external_id}")
        kind_raw = _optional(row, "item_type") or ItemType.UNKNOWN.value
        status_raw = _optional(row, "availability") or Availability.AVAILABLE.value
        try:
            kind = ItemType(kind_raw)
            status = Availability(status_raw)
        except ValueError as exc:
            raise ContentFormatError(f"Неверный тип или статус оферты {external_id}") from exc
        attributes = {"sku_id": sku_id}
        for key in ("delivery_days_min", "delivery_days_max", "valid_from", "valid_to"):
            value = _optional(row, key)
            if value:
                attributes[key] = value
        regions = row.get("delivery_regions", [])
        if not isinstance(regions, list) or any(
            not isinstance(region, str) or not region.strip() for region in regions
        ):
            raise ContentFormatError(f"Неверные регионы оферты {external_id}")
        if regions:
            attributes["delivery_regions"] = "|".join(region.strip() for region in regions)
        article = _optional(row, "article")
        observed_at = datetime.now(UTC)
        return Offer(
            offer_id=identity.offer_id(self._source.source_id, external_id),
            source_id=self._source.source_id,
            external_id=external_id,
            url=url,
            name=name,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
            supplier_id=seller.supplier_id,
            seller_status=VerificationStatus.UNVERIFIED,
            seller_evidence_url=url,
            item_type=kind,
            article=article,
            attributes=attributes,
            price=price,
            currency=_optional(row, "currency"),
            unit=_optional(row, "unit"),
            delivery_regions=tuple(region.strip() for region in regions),
            availability=status,
            content_hash=identity.offer_content_hash(
                name=name,
                item_type=kind.value,
                article=article,
                unit=_optional(row, "unit"),
                attributes=attributes,
            ),
        )


def _required(row: dict[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, (str, int, float)) or not str(value).strip():
        raise ContentFormatError(f"Отсутствует поле {key}")
    return str(value).strip()


def _optional(row: dict[str, object], key: str) -> str:
    value = row.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ContentFormatError(f"Неверное поле {key}")
    return value.strip()


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContentFormatError("Неверное контрольное число экспорта")
    return value
