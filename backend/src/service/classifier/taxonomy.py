"""Правила таксономии: уровень кода, рубрика и тип позиции.

Рубрика не считается отдельной моделью и не угадывается: это проекция кода
ОКПД2 по самому длинному совпавшему префиксу. Тип позиции выводится из класса
кода, а без кода — по устойчивым оборотам названия.
"""

import re
from collections.abc import Mapping, Sequence

from src.models.enums import ItemType

_CODE = re.compile(r"^\d{2}(?:\.\d{1,2}){0,2}(?:\.\d{1,3})?$")


def normalize_code(value: str) -> str:
    """Оставляет код, записанный по формату ОКПД2, иначе пустую строку."""
    code = (value or "").strip()
    return code if _CODE.match(code) else ""


def level_of(code: str) -> int:
    """Число значащих цифр: 2 — класс, 4 — группа, дальше подгруппы."""
    return len(code.replace(".", ""))


def rubric_of(code: str, prefixes: Mapping[str, str]) -> str:
    """Самый длинный совпавший префикс выигрывает."""
    best = ""
    for prefix in prefixes:
        if (code == prefix or code.startswith(f"{prefix}.")) and len(prefix) > len(best):
            best = prefix
    return prefixes.get(best, "")


def item_type_of(code: str, class_types: Mapping[str, str]) -> ItemType:
    if not code:
        return ItemType.UNKNOWN
    name = class_types.get(code[:2], "")
    return ItemType(name) if name else ItemType.UNKNOWN


def item_type_by_phrase(text: str, phrases: Mapping[str, Sequence[str]]) -> tuple[ItemType, str]:
    """Тип по обороту в начале названия: выигрывает самый длинный оборот.

    Оборот ищется только в начале: «Монтаж системы» — это работы, а «Пистолет
    для монтажной пены» — товар, и середина названия о типе ничего не говорит.
    """
    lowered = (text or "").strip().lower()
    best_phrase = ""
    best_type = ItemType.UNKNOWN
    for name, items in phrases.items():
        for phrase in items:
            if lowered.startswith(phrase) and len(phrase) > len(best_phrase):
                best_phrase = phrase
                best_type = ItemType(name)
    return best_type, best_phrase
