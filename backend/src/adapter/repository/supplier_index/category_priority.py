import re

from src.models.search.search_context import SearchContext

_CATEGORY = re.compile(r"\d{2}\.\d{2}(?:\.\d{1,3}){0,2}")


def requested_categories(context: SearchContext | None) -> frozenset[str]:
    return frozenset(
        code[:5] for code in (context.okpd2_codes if context else ()) if _CATEGORY.fullmatch(code)
    )


def supplier_category_coverage(cards: list[dict], categories: frozenset[str]) -> dict[str, int]:
    matched: dict[str, set[str]] = {}
    for card in cards:
        category = card["category"]
        if category in categories:
            matched.setdefault(card["supplier_inn"], set()).add(category)
    return {inn: len(values) for inn, values in matched.items()}
