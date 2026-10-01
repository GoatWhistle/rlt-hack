import re

WEIGHTS_10 = (2, 4, 10, 3, 5, 9, 4, 6, 8)
WEIGHTS_11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
WEIGHTS_12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
COMPANY_LENGTH = 10
PERSON_LENGTH = 12
NON_DIGITS = re.compile(r"\D")


def _check_digit(digits: str, weights: tuple[int, ...]) -> int:
    return (
        sum(int(digit) * weight for digit, weight in zip(digits, weights, strict=False)) % 11 % 10
    )


def is_valid_inn(value: str) -> bool:
    if not value.isascii() or not value.isdigit() or len(set(value)) == 1:
        return False
    if len(value) == COMPANY_LENGTH:
        return _check_digit(value[:9], WEIGHTS_10) == int(value[9])
    if len(value) == PERSON_LENGTH:
        return _check_digit(value[:10], WEIGHTS_11) == int(value[10]) and _check_digit(
            value[:11], WEIGHTS_12
        ) == int(value[11])
    return False


def normalize_inn(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = NON_DIGITS.sub("", raw)
    if len(digits) in (COMPANY_LENGTH - 1, PERSON_LENGTH - 1):
        padded = digits.zfill(len(digits) + 1)
        if is_valid_inn(padded):
            return padded
    return digits if is_valid_inn(digits) else None
