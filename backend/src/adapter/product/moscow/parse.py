"""Преобразование карточки СТЕ в самостоятельный продукт."""

import hashlib
import json
from collections.abc import Mapping
from uuid import NAMESPACE_URL, UUID, uuid5

from src.adapter.product.moscow.errors import MoscowProductFormatError
from src.models.enums import ItemType
from src.models.product import Product


def product_id(source_id: UUID, external_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"moscow-sku:{source_id}:{external_id}")


def parse_product(source_id: UUID, payload: Mapping[str, object]) -> Product:
    raw_id = payload.get("id")
    if not isinstance(raw_id, int | str) or isinstance(raw_id, bool) or not str(raw_id).strip():
        raise MoscowProductFormatError("карточка СТЕ без id")
    external_id = str(raw_id).strip()
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise MoscowProductFormatError(f"СТЕ {external_id}: отсутствует название")
    raw_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    item_type = _item_type(payload.get("itemType"))
    return Product(
        product_id=product_id(source_id, external_id),
        source_id=source_id,
        external_id=external_id,
        url=f"https://zakupki.mos.ru/sku/view/{external_id}",
        name=name.strip(),
        description=_string(payload.get("description")),
        item_type=item_type,
        category_id=_string(payload.get("categoryId")),
        unit=_string(payload.get("unitName")),
        brand=_string(payload.get("brandName")),
        manufacturer=_string(payload.get("manufacturerName")),
        country=_string(payload.get("countryName")),
        raw_json=raw_json,
        content_hash=hashlib.sha256(raw_json.encode()).hexdigest(),
    )


def _string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _item_type(value: object) -> ItemType:
    if isinstance(value, str):
        return {
            "goods": ItemType.GOODS,
            "work": ItemType.WORK,
            "service": ItemType.SERVICE,
        }.get(value.lower(), ItemType.UNKNOWN)
    return ItemType.UNKNOWN
