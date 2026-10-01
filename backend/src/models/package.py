"""Пакет данных источника: всё, что отдаёт один адаптер за обход.

Пакет — полное состояние источника на момент обхода: его компании и их
предложения. Адаптер собирает его целиком и отдаёт сервису готовым, поэтому
сохранение пакета заменяет накопленные пачки, курсоры и свидетельства.
"""

from dataclasses import dataclass

from src.models.offer import Offer
from src.models.source import Source
from src.models.supplier import Supplier


@dataclass(frozen=True, slots=True)
class SupplierPackage:
    source: Source
    suppliers: tuple[Supplier, ...] = ()
    offers: tuple[Offer, ...] = ()
