"""Преобразование карточки СТЕ в самостоятельный продукт."""

import hashlib
import json
from collections.abc import Mapping
from uuid import NAMESPACE_URL, UUID, uuid5

from src.adapter.product.moscow.errors import MoscowProductFormatError
from src.models.catalog.product import Product
from src.models.enums import ItemType

EXCLUDED_FIELDS = {
    "companyId",
    "originUserId",
    "originUserLogin",
    "offersCount",
    "views",
    "contractsCount",
    "costPerUnit",
    "avgPrice",
    "medianPrice",
    "minPrice",
    "maxPrice",
    "referencePrice",
    "limitedPrice",
    "limitedPriceHistoryItems",
    "currencyShortName",
    "inComparison",
}


def product_id(source_id: UUID, external_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"moscow-sku:{source_id}:{external_id}")


def parse_product(
    source_id: UUID,
    payload: Mapping[str, object],
    category_path: tuple[str, ...] = (),
    *,
    full_card: bool = False,
) -> Product:
    raw_id = payload.get("id")
    if not isinstance(raw_id, int | str) or isinstance(raw_id, bool) or not str(raw_id).strip():
        raise MoscowProductFormatError("карточка СТЕ без id")
    external_id = str(raw_id).strip()
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise MoscowProductFormatError(f"СТЕ {external_id}: отсутствует название")
    product_fields = {key: value for key, value in payload.items() if key not in EXCLUDED_FIELDS}
    raw_json = json.dumps(
        _without_empty(product_fields),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    directory = _mapping(payload.get("productionDirectory"))
    production = _mapping(payload.get("production"))
    okpd = _mapping(production.get("okpd"))
    tree_path = _string(payload.get("productionDirectoryTreePathId")) or _string(
        payload.get("productionDirectoryPath")
    )
    classifier_codes = {}
    for code_name, value in (
        ("production", production.get("code") or payload.get("productionCode")),
        ("okpd2", okpd.get("code")),
    ):
        if isinstance(value, str) and value.strip():
            classifier_codes[code_name] = value.strip()
    image_urls = _image_urls(
        payload.get("images"), payload.get("skuImageIds"), payload.get("skuImageId")
    )
    category_name = _string(directory.get("name")) or _string(
        payload.get("productionDirectoryName")
    )
    return Product(
        product_id=product_id(source_id, external_id),
        source_id=source_id,
        external_id=external_id,
        url=f"https://zakupki.mos.ru/sku/view/{external_id}",
        name=name.strip(),
        description=_string(payload.get("description")),
        item_type=_item_type(tree_path),
        category_id=_string_id(payload.get("productionDirectoryId")),
        category_path=category_path or ((category_name,) if category_name else ()),
        classifier_codes=classifier_codes,
        attributes=_attributes(payload.get("skuCharacteristics")),
        unit=_string(payload.get("okeiShortName")) or _string(payload.get("okeiName")),
        manufacturer=_string(payload.get("manufacturerName")),
        country=_string(payload.get("oksmName")),
        image_urls=image_urls,
        detail_status="full" if full_card else "summary_only",
        raw_json=raw_json,
        content_hash=hashlib.sha256(raw_json.encode()).hexdigest(),
    )


def _string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_id(value: object) -> str:
    return str(value) if isinstance(value, int | str) and not isinstance(value, bool) else ""


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _without_empty(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _without_empty(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_without_empty(item) for item in value]
    return value


def _item_type(tree_path: str) -> ItemType:
    return {
        ".1.": ItemType.GOODS,
        ".2.": ItemType.WORK,
        ".3.": ItemType.SERVICE,
    }.get(tree_path[:3], ItemType.UNKNOWN)


def _attributes(value: object) -> dict[str, str]:
    if not isinstance(value, list):
        return {}
    result: dict[str, str] = {}
    for characteristic in value:
        if not isinstance(characteristic, Mapping):
            continue
        definition = _mapping(characteristic.get("productCharacteristicValue"))
        name = _string(definition.get("productCharacteristicName"))
        if not name:
            continue
        values = (
            characteristic.get("characteristicValueStringValue"),
            characteristic.get("characteristicValueIntValue"),
            characteristic.get("characteristicValueDecimalValue"),
            characteristic.get("characteristicValueBoolValue"),
            characteristic.get("characteristicValueDateTimeValue"),
            characteristic.get("rangeValue"),
        )
        actual = next((item for item in values if item is not None), None)
        if actual is None:
            continue
        text = str(actual).lower() if isinstance(actual, bool) else str(actual).strip()
        unit = _string(definition.get("productCharacteristicUnitDesignationNational"))
        if unit:
            text = f"{text} {unit}"
        key = name
        suffix = 2
        while key in result:
            key = f"{name} #{suffix}"
            suffix += 1
        result[key] = text
    return result


def _image_urls(value: object, fallback: object, primary: object) -> tuple[str, ...]:
    ids: list[int] = []
    if isinstance(value, list):
        for image in value:
            identifier = _mapping(image).get("fileStorageId")
            if isinstance(identifier, int) and identifier > 0:
                ids.append(identifier)
    if isinstance(fallback, list):
        ids.extend(
            identifier for identifier in fallback if isinstance(identifier, int) and identifier > 0
        )
    if isinstance(primary, int) and primary > 0:
        ids.append(primary)
    return tuple(
        f"https://zakupki.mos.ru/newapi/api/FileStorage/Download?id={i}" for i in dict.fromkeys(ids)
    )
