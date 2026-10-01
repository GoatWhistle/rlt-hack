"""Отчёт о покрытии: сколько позиций удалось привести к единому виду.

Это метрика подготовки данных, а не качества модели: она показывает, какими
каналами получены коды и сколько позиций осталось без кода честно.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Share:
    name: str
    offers: int


@dataclass(frozen=True, slots=True)
class CoverageReport:
    offers: int = 0
    normalized: int = 0
    classified: int = 0
    with_rubric: int = 0
    with_unit: int = 0
    with_price_per_unit: int = 0
    with_brand: int = 0
    with_article: int = 0
    with_attributes: int = 0
    by_method: tuple[Share, ...] = ()
    by_rubric: tuple[Share, ...] = ()
    by_item_type: tuple[Share, ...] = ()
    by_level: tuple[Share, ...] = ()
