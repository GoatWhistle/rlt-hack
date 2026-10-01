"""Разметка JSON-LD: узлы schema.org со страницы и приведение их значений.

Разметку источник публикует для поисковых систем, поэтому она описывает те же
данные, что и вёрстка, но без догадок о классах и порядке блоков. Повреждённый
блок пропускается: остальная страница от этого не теряется.
"""

import json
from decimal import Decimal, InvalidOperation
from typing import Any

PRODUCT_TYPES = frozenset({"Product", "IndividualProduct", "ProductModel", "Service"})

ORGANIZATION_TYPES = frozenset({"Organization", "LocalBusiness", "Corporation"})


def nodes(tree: Any) -> list[dict[str, Any]]:
    """Все узлы разметки страницы: вложения `@graph` и списки развёрнуты."""
    found: list[dict[str, Any]] = []
    for script in tree.iter("script"):
        if (script.get("type") or "").strip().lower() != "application/ld+json":
            continue
        raw = (script.text_content() or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except ValueError:
            # Некорректный JSON-LD пропускаем: страница может быть валидной в остальном.
            continue
        found.extend(_flatten(payload))
    return found


def of_types(found: list[dict[str, Any]], types: frozenset[str]) -> list[dict[str, Any]]:
    return [node for node in found if types & type_names(node)]


def first_of_types(found: list[dict[str, Any]], types: frozenset[str]) -> dict[str, Any]:
    matched = of_types(found, types)
    return matched[0] if matched else {}


def type_names(node: dict[str, Any]) -> set[str]:
    types = node.get("@type", "")
    return {types} if isinstance(types, str) else set(types or ())


def first(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
        return {}
    return value if isinstance(value, dict) else {}


def text(value: Any) -> str:
    if value is None or isinstance(value, (dict, list)):
        return ""
    return " ".join(str(value).split())


def strings(value: Any) -> tuple[str, ...]:
    """Значение свойства как набор строк: одиночное значение тоже список."""
    items = value if isinstance(value, list) else [value]
    found: list[str] = []
    for item in items:
        line = text(item.get("name")) if isinstance(item, dict) else text(item)
        if line and line not in found:
            found.append(line)
    return tuple(found)


def number(value: Any) -> Decimal | None:
    raw = text(value).replace(",", ".").replace(" ", "")
    if not raw:
        return None
    try:
        parsed = Decimal(raw)
    except InvalidOperation:
        return None
    return parsed if parsed >= 0 else None


def _flatten(payload: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(payload, list):
        for item in payload:
            found.extend(_flatten(item))
        return found
    if not isinstance(payload, dict):
        return found
    if "@graph" in payload:
        found.extend(_flatten(payload["@graph"]))
    found.append(payload)
    return found
