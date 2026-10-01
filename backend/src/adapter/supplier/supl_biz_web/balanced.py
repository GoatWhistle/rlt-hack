"""Равномерная по корневым категориям выборка товаров Supl.biz.

Случайная выборка из sitemap отражает вес категорий каталога: «Оборудование и
инструменты» составляет почти треть. Здесь на каждую корневую категорию берётся
одинаковая квота, а внутри категории товары распределяются поровну между её
подкатегориями. Это диагностическая выборка, а не полный снимок источника.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from src.adapter.supplier.supl_biz_web.categories import RootCategory


@dataclass(frozen=True, slots=True)
class RootPlan:
    root: RootCategory
    urls: tuple[str, ...]
    available: int


def allocate(
    root: RootCategory,
    listings: Sequence[Sequence[str]],
    quota: int,
    taken: set[str],
) -> RootPlan:
    """Выбирает до `quota` адресов: по кругу по одному из каждой подкатегории.

    Адреса, уже взятые другими категориями, пропускаются: товар числится только
    за той категорией, которая встретила его первой.
    """
    queues = [[url for url in listing if url not in taken] for listing in listings]
    available = len({url for queue in queues for url in queue})
    chosen: list[str] = []
    position = 0
    while len(chosen) < quota and any(position < len(queue) for queue in queues):
        for queue in queues:
            if len(chosen) >= quota:
                break
            if position < len(queue) and queue[position] not in taken:
                taken.add(queue[position])
                chosen.append(queue[position])
        position += 1
    return RootPlan(root, tuple(chosen), available)
