"""Проверка и поиск ИНН и КПП в тексте документа.

Контрольные цифры подтверждают только формат номера. Существование компании и
соответствие реквизитов проверяется по реестру, а не этим модулем.
"""

import re

from src.models.inn import is_valid_inn as is_valid_inn
from src.models.inn import normalize_inn as normalize_inn

_INN_IN_TEXT = re.compile(r"ИНН\D{0,10}(\d{10}|\d{12})", re.IGNORECASE)
_KPP_IN_TEXT = re.compile(r"КПП\D{0,10}(\d{9})", re.IGNORECASE)


def normalize_kpp(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return digits if len(digits) == 9 else None


def find_inn(text: str) -> str | None:
    """Ищет ИНН рядом с подписью: произвольное 10-значное число им не является."""
    for match in _INN_IN_TEXT.finditer(text):
        candidate = normalize_inn(match.group(1))
        if candidate:
            return candidate
    return None


def find_kpp(text: str) -> str | None:
    match = _KPP_IN_TEXT.search(text)
    return normalize_kpp(match.group(1)) if match else None
