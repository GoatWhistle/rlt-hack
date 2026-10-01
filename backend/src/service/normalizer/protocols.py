"""Интерфейсы, которые потребляет нормализатор.

Справочники загружаются один раз при сборке зависимостей — асинхронно, из
файлов или другого хранилища. Поиск по загруженному справочнику остаётся чистой
функцией в памяти и не блокирует событийный цикл, поэтому методы синхронные.
"""

from collections.abc import Iterable, Mapping
from typing import Protocol


class Unit(Protocol):
    """Единица измерения ОКЕИ и её приведение к базовой."""

    @property
    def code(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def base(self) -> str: ...

    @property
    def factor(self) -> float: ...


class UnitReference(Protocol):
    def resolve(self, text: str) -> Unit | None:
        """Находит единицу по написанию или синониму."""

    def is_measure(self, unit: Unit) -> bool:
        """Непрерывная мера — длина, масса, объём, площадь: её можно делить."""

    def name_of(self, code: str) -> str: ...


class TextRules(Protocol):
    @property
    def months(self) -> Mapping[str, str]: ...

    @property
    def abbreviations(self) -> Mapping[str, str]: ...

    @property
    def synonyms(self) -> Mapping[str, str]: ...

    @property
    def noise(self) -> Iterable[str]: ...

    @property
    def attribute_keys(self) -> Mapping[str, str]: ...

    @property
    def currencies(self) -> Mapping[str, str]: ...
