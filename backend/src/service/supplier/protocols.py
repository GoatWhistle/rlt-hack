"""Интерфейсы, которые потребляет сервис сбора поставщиков.

Единый контракт источника — SupplierProvider: адаптер сам знает свой адрес,
разметку и правила разбора, а сервису отдаёт готовый пакет с компаниями и
предложениями. Подключение нового источника не меняет ни сервис, ни хранилище.
"""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.models.journal import CrawlRun
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
