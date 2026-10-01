"""Интерфейсы, которые потребляет классификатор.

Справочники отдают данные, а правила по ним применяет сервис: проекция кода в
рубрику, тип позиции и уровень подробности — это бизнес-логика, и она не должна
переезжать в адаптер вместе с файлом. Справочники загружаются один раз
асинхронно, поэтому поиск по ним синхронный и не блокирует цикл. Архив закупок
читается из хранилища, поэтому его метод асинхронный.
"""

from collections.abc import Mapping, Sequence
from typing import Protocol


class Okpd2Reference(Protocol):
    def code_by_name(self, normalized_name: str) -> str | None:
        """Код по точному совпадению с официальным наименованием."""

    def name_of(self, code: str) -> str:
        """Наименование кода или ближайшего известного уровня."""

    def has_class(self, code: str) -> bool:
        """Существует ли класс (первые две цифры) кода."""


class RubricReference(Protocol):
    @property
    def prefixes(self) -> Mapping[str, str]:
        """Префикс ОКПД2 — код рубрики; выигрывает самый длинный."""

    @property
    def names(self) -> Mapping[str, str]:
        """Код рубрики — её название для интерфейса."""

    @property
    def class_types(self) -> Mapping[str, str]:
        """Класс ОКПД2 — тип позиции: товар, работа или услуга."""

    @property
    def type_phrases(self) -> Mapping[str, Sequence[str]]:
        """Обороты названия, по которым тип виден без кода."""


class LexiconReference(Protocol):
    @property
    def entries(self) -> Sequence[tuple[tuple[str, ...], str]]:
        """Основы слов головного понятия и код ОКПД2 для него."""


class SourceCategoryReference(Protocol):
    def code_by_category(self, provider_name: str, category: str) -> str | None:
        """Код по разделу каталога источника."""


class ArchiveCatalog(Protocol):
    async def load_items(self, limit: int) -> list[tuple[str, str]]:
        """Пары «название позиции — код ОКПД2» из архива закупок."""
