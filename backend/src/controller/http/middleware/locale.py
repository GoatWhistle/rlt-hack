from typing import Annotated

from fastapi import Header

from src.models.enums import Locale

DEFAULT_LOCALE = Locale.RU
SUPPORTED = {locale.value: locale for locale in Locale}


def language_weight(part: str) -> tuple[str, float]:
    tag, *parameters = (piece.strip() for piece in part.split(";"))
    weight = 1.0
    for parameter in parameters:
        name, _, value = parameter.partition("=")
        if name.strip().lower() == "q":
            try:
                weight = float(value)
            except ValueError:
                weight = 0.0
    return tag.split("-")[0].lower(), weight


def parse_accept_language(header: str | None) -> Locale:
    if not header:
        return DEFAULT_LOCALE
    ranges = [language_weight(part) for part in header.split(",") if part.strip()]
    accepted = (entry for entry in ranges if entry[1] > 0)
    for tag, _ in sorted(accepted, key=lambda entry: entry[1], reverse=True):
        if tag in SUPPORTED:
            return SUPPORTED[tag]
    return DEFAULT_LOCALE


async def request_locale(
    accept_language: Annotated[str | None, Header()] = None,
) -> Locale:
    return parse_accept_language(accept_language)
