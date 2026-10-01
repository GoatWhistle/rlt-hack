"""Деление готового пакета на порции для обогащения, разбора и записи.

Потоковый адаптер отдаёт порции сам, остальные собирают пакет целиком. Чтобы
обогащение, нормализация, классификация и запись шли одинаковыми порциями для
всех источников, собранный пакет делится здесь.

Компании идут первыми и отдельно от предложений: обогащение работает только с
компаниями, нормализация и классификация — только с предложениями, поэтому
разделение не меняет результат ни одного шага. Компания при этом записывается
один раз, а не повторяется в каждой порции своих предложений.
"""

import dataclasses
from collections.abc import Iterator, Sequence

from src.models.package import SupplierPackage


def package_batches(package: SupplierPackage, batch_size: int) -> Iterator[SupplierPackage]:
    """Порции пакета: сначала компании, затем предложения.

    Пустой пакет отдаёт одну пустую порцию: по ней вызывающий код отличает
    успешный обход без данных от обхода, прерванного ошибкой.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    empty = True
    for batch in _chunks(package.suppliers, batch_size):
        empty = False
        yield dataclasses.replace(package, suppliers=batch, offers=())
    for batch in _chunks(package.offers, batch_size):
        empty = False
        yield dataclasses.replace(package, suppliers=(), offers=batch)
    if empty:
        yield dataclasses.replace(package, suppliers=(), offers=())


def _chunks[T](items: Sequence[T], size: int) -> Iterator[tuple[T, ...]]:
    for offset in range(0, len(items), size):
        yield tuple(items[offset : offset + size])
