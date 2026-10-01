"""Дерево категорий Supl.biz и списки товаров категорий.

Страница `/proposals/` содержит в `preloadedState` дерево из корневых категорий
с подкатегориями, а страница категории — первые 40 товаров. Листание закрыто в
`robots.txt` (параметры `page`, `sort`), поэтому берётся только первая страница
каждой подкатегории. DTO внешнего формата остаются здесь.
"""

import json
import re
from dataclasses import dataclass
from typing import Any

from src.adapter.supplier.errors import ContentFormatError
from src.adapter.supplier.supl_biz_web.state import BASE_URL

# Продавцы-спамеры размещают товар в десятках несвязанных категорий: у обычного
# товара в списке одна-две категории, поэтому такие позиции в выборку не берутся.
MAX_LISTING_CATEGORIES = 3

_STATE = re.compile(
    r'<script id="preloadedState" type="application/json">\s*(.*?)</script>', re.DOTALL
)


@dataclass(frozen=True, slots=True)
class Subcategory:
    category_id: int
    slug: str
    name: str

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.slug}-category{self.category_id}/"


@dataclass(frozen=True, slots=True)
class RootCategory:
    category_id: int
    name: str
    children: tuple[Subcategory, ...]


def _state(html: str, url: str) -> dict[str, Any]:
    match = _STATE.search(html)
    if match is None:
        raise ContentFormatError(f"{url}: на странице нет состояния preloadedState")
    try:
        state = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise ContentFormatError(f"{url}: состояние страницы не разобрано: {error}") from error
    if not isinstance(state, dict):
        raise ContentFormatError(f"{url}: состояние страницы не является объектом")
    return state


def parse_tree(html: str, url: str) -> tuple[RootCategory, ...]:
    """Корневые категории с подкатегориями; категории для взрослых пропускаются."""
    state = _state(html, url)
    try:
        nodes = state["shared"]["category"]["data"]
        roots = tuple(
            RootCategory(
                category_id=int(node["id"]),
                name=" ".join(str(node["name"]).split()),
                children=tuple(
                    Subcategory(int(child["id"]), str(child["slug"]), str(child["name"]))
                    for child in node["children"]
                ),
            )
            for node in nodes
            if not node.get("forAdult")
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ContentFormatError(f"{url}: в состоянии страницы нет дерева категорий") from error
    if not roots or not all(root.children for root in roots):
        raise ContentFormatError(f"{url}: дерево категорий пусто или без подкатегорий")
    return roots


def parse_listing(html: str, url: str) -> list[str]:
    """Адреса товаров первой страницы категории без размещённых во многих категориях.

    Пустая категория даёт пустой список.
    """
    state = _state(html, url)
    try:
        hits = state["catalog"]["proposals"]["proposals"]["data"]["hits"]
        return [
            f"{BASE_URL}/{hit['slug']}-p{hit['id']}/"
            for hit in hits
            if len(hit.get("categories") or ()) <= MAX_LISTING_CATEGORIES
        ]
    except (KeyError, TypeError) as error:
        raise ContentFormatError(f"{url}: в состоянии страницы нет списка товаров") from error
