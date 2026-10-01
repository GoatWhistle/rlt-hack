import re
from decimal import Decimal

from src.models.query_item import Quantity

UNITS: tuple[tuple[str, str], ...] = (
    ("м2", r"м2|м²|кв\.?\s?м(?:етр(?:а|ов)?)?"),
    ("м3", r"м3|м³|куб\.?\s?м(?:етр(?:а|ов)?)?"),
    ("кг", r"кг|килограмм(?:а|ов)?"),
    ("мл", r"мл|миллилитр(?:а|ов)?"),
    ("км", r"км|километр(?:а|ов)?"),
    ("т", r"тонн(?:а|ы)?|тн|т"),
    ("г", r"грамм(?:а|ов)?|гр|г"),
    ("шт", r"штук(?:а|и)?|шт"),
    ("л", r"литр(?:а|ов)?|л"),
    ("м", r"метр(?:а|ов)?|пог\.?\s?м|м"),
    ("упак", r"упаков(?:ка|ки|ок)|упак|уп"),
    ("пачка", r"пач(?:ка|ки|ек)|пач"),
    ("рулон", r"рулон(?:а|ов)?|рул"),
    ("компл", r"комплект(?:а|ов)?|компл|к-т"),
    ("коробка", r"короб(?:ка|ки|ок)|кор"),
    ("пара", r"пар(?:а|ы)?"),
    ("лист", r"лист(?:а|ов)?"),
    ("мешок", r"меш(?:ок|ка|ков)|меш"),
    ("бутылка", r"бутыл(?:ка|ки|ок)|бут"),
)

UNIT_ALTERNATIVES = "|".join(pattern for _, pattern in UNITS)
CANONICAL_UNITS = tuple((unit, re.compile(pattern)) for unit, pattern in UNITS)
QUANTITY = re.compile(
    r"(?<![\w.,×*/])"
    r"(?P<value>\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    rf"\s*(?P<unit>{UNIT_ALTERNATIVES})\.?"
    r"(?![\w/²³])",
    re.IGNORECASE,
)


def canonical_unit(raw: str) -> str:
    lowered = raw.lower().rstrip(".")
    return next(unit for unit, pattern in CANONICAL_UNITS if pattern.fullmatch(lowered))


def parse_quantity(match: re.Match[str]) -> Quantity | None:
    digits = re.sub(r"[  ]", "", match.group("value")).replace(",", ".")
    value = Decimal(digits)
    if value <= 0:
        return None
    return Quantity(value=value, unit=canonical_unit(match.group("unit")))


def extract_quantity(text: str) -> tuple[Quantity | None, str]:
    matches = list(QUANTITY.finditer(text))
    for match in reversed(matches):
        quantity = parse_quantity(match)
        if quantity is not None:
            return quantity, text[: match.start()] + " " + text[match.end() :]
    return None, text
