"""Проверка и поиск ИНН и КПП в тексте документа.

Контрольные цифры подтверждают только формат номера. Существование компании и
соответствие реквизитов проверяется по реестру, а не этим модулем.
"""

import re

_INN_WEIGHTS_10 = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN_WEIGHTS_11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN_WEIGHTS_12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)

_INN_IN_TEXT = re.compile(r"ИНН\D{0,10}(\d{10}|\d{12})", re.IGNORECASE)
_KPP_IN_TEXT = re.compile(r"КПП\D{0,10}(\d{9})", re.IGNORECASE)


def _checksum(digits: str, weights: tuple[int, ...]) -> int:
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights, strict=False))
    return total % 11 % 10


def is_valid_inn(value: str) -> bool:
    if not value.isdigit():
        return False
    # Номер из одной повторяющейся цифры проходит контрольную сумму, но реальной
    # компании не соответствует: такие значения встречаются как заполнители.
    if len(set(value)) == 1:
        return False
    if len(value) == 10:
        return _checksum(value[:9], _INN_WEIGHTS_10) == int(value[9])
    if len(value) == 12:
        return _checksum(value[:10], _INN_WEIGHTS_11) == int(value[10]) and _checksum(
            value[:11], _INN_WEIGHTS_12
        ) == int(value[11])
    return False


def normalize_inn(raw: str | None) -> str | None:
    """Возвращает ИНН без разделителей или None, если номер не прошёл проверку."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    # Ведущий ноль теряется, если выгрузка прошла через числовой тип.
    if len(digits) in (9, 11):
        padded = digits.zfill(len(digits) + 1)
        if is_valid_inn(padded):
            return padded
    return digits if is_valid_inn(digits) else None


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
