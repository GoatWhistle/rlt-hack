"""Нормализованное представление позиции: производное от исходных полей.

Исходные значения не затираются: нормализатор кладёт результат рядом отдельной
моделью, а версия алгоритма позволяет узнать устаревшие записи и пересчитать
только их.
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Normalization:
    # Ядро названия: предмет без бренда, артикула, ГОСТа и рекламного шума.
    name: str = ""
    # Ключ склейки дублей: бренд и артикул, иначе ядро названия.
    key: str = ""
    brand: str = ""
    article: str = ""
    # Характеристики с каноническими ключами: исходная карта остаётся нетронутой.
    attributes: dict[str, str] = field(default_factory=dict)
    # Код единицы измерения по ОКЕИ и базовая единица сравнения.
    unit_code: str = ""
    unit_name: str = ""
    price_per_unit: Decimal | None = None
    price_unit_code: str = ""
    # Код валюты по ISO: источники пишут рубль и как RUR, и как RUB.
    currency: str = ""
    algorithm_version: str = ""
