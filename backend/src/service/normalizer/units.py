"""Единицы измерения и цена за базовую единицу.

Без общей единицы цены несравнимы: «упаковка 500 листов за 300 рублей» и «лист
за 0,6 рубля» должны приводиться к одному знаменателю. Делится только
непрерывная мера и фасовка с известным количеством — цену за штуку ни на что не
делят.
"""

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from src.service.normalizer.protocols import Unit, UnitReference

PIECE = "796"
PACKAGING = ("778", "736", "704", "839")
PRICE_EXPONENT = Decimal("0.0001")


class UnitPrice(NamedTuple):
    price: Decimal | None
    unit_code: str


def resolve(unit_text: str, attributes: Mapping[str, str], units: UnitReference) -> Unit | None:
    """Единица берётся из поля источника, иначе из его характеристик."""
    for candidate in (unit_text, attributes.get("unit", ""), attributes.get("packaging", "")):
        unit = units.resolve(candidate) if candidate else None
        if unit is not None:
            return unit
    return None


def price_per_unit(
    price: Decimal | None,
    unit: Unit | None,
    attributes: Mapping[str, str],
    units: UnitReference,
) -> UnitPrice:
    """Цена за базовую единицу: метр, килограмм, литр или штуку."""
    if price is None or unit is None:
        return UnitPrice(None, "")
    if units.is_measure(unit):
        factor = Decimal(str(unit.factor))
        if factor <= 0:
            return UnitPrice(None, "")
        return UnitPrice(_round(price / factor), unit.base)
    quantity = _quantity(attributes)
    if unit.code in PACKAGING and quantity is not None and quantity > 0:
        return UnitPrice(_round(price / quantity), PIECE)
    return UnitPrice(_round(price), unit.base)


def currency(code: str, codes: Mapping[str, str]) -> str:
    """Сводит написание валюты к одному коду ISO."""
    key = (code or "").strip().lower()
    return codes.get(key, code.strip().upper() if key else "")


def _quantity(attributes: Mapping[str, str]) -> Decimal | None:
    raw = attributes.get("pack_quantity") or attributes.get("quantity") or ""
    digits = "".join(character for character in raw if character.isdigit() or character == ".")
    try:
        return Decimal(digits) if digits else None
    except InvalidOperation:
        return None


def _round(value: Decimal) -> Decimal:
    return value.quantize(PRICE_EXPONENT)
