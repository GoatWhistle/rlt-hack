"""Характеристики к общему словарю: разные написания одного свойства — один ключ.

Исходная карта характеристик остаётся нетронутой: канонические ключи попадают в
отдельное поле нормализации. Неизвестный ключ не выбрасывается — он остаётся под
своим очищенным именем, иначе данные источника терялись бы молча.
"""

from collections.abc import Mapping

from src.service.normalizer.protocols import TextRules
from src.service.normalizer.text import clean, fix_numbers

MAX_VALUE_LENGTH = 200


def canonical(attributes: Mapping[str, str], rules: TextRules) -> dict[str, str]:
    """Переименовывает известные ключи и лечит значения."""
    result: dict[str, str] = {}
    for raw_key, raw_value in attributes.items():
        key = clean(raw_key).lower()
        if not key:
            continue
        value = fix_numbers(clean(raw_value), rules.months)[:MAX_VALUE_LENGTH]
        if not value:
            continue
        result.setdefault(rules.attribute_keys.get(key, key), value)
    return result


def merge(first: Mapping[str, str], second: Mapping[str, str]) -> dict[str, str]:
    """Значения из названия не вытесняют то, что источник указал явно."""
    merged = dict(second)
    for key, value in first.items():
        merged.setdefault(key, value)
    return merged
