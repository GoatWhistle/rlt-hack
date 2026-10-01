"""Интерфейсы, которые потребляет сервис сбора поставщиков.

Единый контракт источника — SupplierProvider: адаптер сам знает свой адрес,
разметку и правила разбора, а сервису отдаёт готовый пакет с компаниями и
предложениями. Подключение нового источника не меняет ни сервис, ни хранилище.

Нормализация и классификация подключаются такими же интерфейсами: сервис сбора
вызывает их по контракту и не знает ни их правил, ни справочников. Порядок
обязателен — классификатор работает с нормализованным названием.
"""

from collections.abc import AsyncIterator, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from src.models.coverage import CoverageReport
from src.models.journal import CrawlRun
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source


class SupplierProvider(Protocol):
    """Обходит один источник и отдаёт его компании и предложения."""

    @property
    def source(self) -> Source:
        """Паспорт источника, который объявляет адаптер."""

    async def fetch(self) -> SupplierPackage:
        """Собирает пакет источника целиком.

        Пропуск отдельной страницы адаптер решает сам, а полный провал обхода
        поднимает исключением: сервис запишет его в журнал обхода.
        """


class OfferNormalizing(Protocol):
    """Приводит позиции пакета к единой форме."""

    async def normalize(self, package: SupplierPackage) -> SupplierPackage: ...

    @property
    def version(self) -> str:
        """Версия правил: по ней видно, какие записи устарели."""


class OfferClassifying(Protocol):
    """Проставляет позициям код ОКПД2, рубрику и тип."""

    async def classify(self, package: SupplierPackage) -> SupplierPackage: ...

    @property
    def version(self) -> str: ...


class OfferCatalog(Protocol):
    """Чтение и перезапись уже сохранённых позиций: пересчёт производных."""

    async def list_by_source(self, source_id: UUID, limit: int, offset: int) -> list[Offer]: ...

    async def save_many(self, offers: Sequence[Offer], updated_at: datetime) -> None: ...

    async def delete_stale(self, source_id: UUID, written_at: datetime) -> int:
        """Помечает удалёнными строки источника старше отметки перезаписи.

        Нужна смене ключа идентичности: после перезаписи всех позиций под
        новыми ID старые строки опознаются по отметке времени, а не списком —
        идентификаторов тысячи, и в параметры запроса они не помещаются.
        """

    async def coverage(self) -> CoverageReport: ...


class OfferIdentity(Protocol):
    """Правила идентичности предложения: они живут в адаптерах источников."""

    def rekey(self, previous: str, url: str, name: str) -> str:
        """Переводит сохранённый ключ источника на действующее правило."""

    def offer_id(self, source_id: UUID, external_id: str) -> UUID: ...


class SourceCatalog(Protocol):
    async def list_all(self) -> list[Source]: ...


class SupplierStorage(Protocol):
    async def save_package(self, package: SupplierPackage) -> int:
        """Сохраняет источник, его компании и предложения одной операцией.

        Предложения источника, которых в пакете нет, снимаются с продажи.
        Возвращает их число.
        """


class CrawlJournal(Protocol):
    async def save_run(self, run: CrawlRun) -> None: ...

    async def last_runs(self, source_id: UUID, limit: int = 10) -> list[CrawlRun]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class StreamingSupplierProvider(Protocol):
    def batches(self, batch_size: int) -> AsyncIterator[SupplierPackage]:
        """Частичные пакеты; нормальное завершение означает полный обход."""
        ...


@runtime_checkable
class StreamingSupplierStorage(Protocol):
    async def save_batch(self, package: SupplierPackage, observed_at: datetime) -> None:
        """Сохраняет порцию без снятия остальных товаров с продажи."""
        ...

    async def finish_snapshot(self, source_id: UUID, observed_at: datetime) -> int: ...


@runtime_checkable
class ResumableSupplierProvider(Protocol):
    async def resume(self, started_at: datetime) -> datetime:
        """Возвращает исходную отметку незавершённого обхода."""
        ...

    @property
    def saved_offer_count(self) -> int: ...

    async def complete(self) -> None:
        """Очищает прогресс после завершения снимка в хранилище."""
        ...
