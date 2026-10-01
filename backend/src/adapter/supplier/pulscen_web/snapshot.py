"""Диагностический источник: снимок страниц Пульса цен из JSON-файла.

Файл собирает консольный скрипт в браузере владельца аккаунта: адаптер к сайту
не обращается. Снимок неполный (несколько рубрик), поэтому он сохраняется
отдельным источником `pulscen_snapshot` и не заменяет полный обход `pulscen_web`.
"""

import asyncio
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.pulscen_web import parsing
from src.adapter.supplier.pulscen_web.builders import ModelBuilder
from src.models.enums import Availability, SupplierRole
from src.models.package import SupplierPackage
from src.models.source import Source

PROVIDER_NAME = "pulscen_snapshot"

_AVAILABILITY = {
    "instock": Availability.AVAILABLE,
    "outofstock": Availability.UNAVAILABLE,
    "preorder": Availability.ON_ORDER,
    "backorder": Availability.ON_ORDER,
}

_ROLES = {
    "Производитель": SupplierRole.MANUFACTURER,
    "Оптовый продавец": SupplierRole.DISTRIBUTOR,
    "Розничный продавец": SupplierRole.RESELLER,
    "Услуги и сервис": SupplierRole.SERVICE_PROVIDER,
}


class PulscenSnapshotProvider:
    def __init__(self, source_defaults: Source, snapshot_path: Path) -> None:
        self._source = source_defaults
        self._path = snapshot_path
        self._builder = ModelBuilder(source_defaults)

    @property
    def source(self) -> Source:
        return self._source

    async def fetch(self) -> SupplierPackage:
        try:
            raw = await asyncio.to_thread(self._path.read_text, "utf-8")
        except OSError as error:
            raise SourceUnavailableError(f"{self._path}: {error}") from error
        try:
            data = json.loads(raw)
            companies = {
                key: _company(key, value) for key, value in dict(data["companies"]).items()
            }
            products = [_product(key, value) for key, value in dict(data["products"]).items()]
        except (ValueError, KeyError, TypeError, InvalidOperation) as error:
            raise ContentFormatError(f"{self._path}: неверный формат снимка: {error}") from error
        if not companies and not products:
            raise ContentFormatError(f"{self._path}: снимок пуст")
        return SupplierPackage(
            source=self._source,
            suppliers=tuple(self._builder.supplier(company) for company in companies.values()),
            offers=tuple(self._builder.offer(product, None) for product in products),
        )


def _company(company_id: str, value: dict[str, Any]) -> parsing.ListedCompany:
    roles = tuple(_ROLES[label] for label in value.get("r", []) if label in _ROLES)
    return parsing.ListedCompany(
        company_id=str(company_id),
        name=str(value["n"]),
        website=str(value.get("w") or ""),
        address=str(value.get("a") or ""),
        roles=roles,
    )


def _product(product_id: str, value: dict[str, Any]) -> parsing.ListedProduct:
    price = value.get("p")
    return parsing.ListedProduct(
        external_id=str(product_id),
        url="https://" + str(value["u"]).removeprefix("https://"),
        name=str(value["n"]),
        price=Decimal(str(price)) if price is not None else None,
        currency=str(value.get("c") or ""),
        availability=_AVAILABILITY.get(str(value.get("a") or "").casefold(), Availability.UNKNOWN),
    )
