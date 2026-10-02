"""Интерфейсы, которые потребляет команда запуска джобы."""

from typing import Protocol
from uuid import UUID

from src.models.coverage import CoverageReport
from src.models.enrichment import EnrichmentResult, RegistryImportResult, ReidentifyResult
from src.models.journal import CrawlRun, SyncResult
from src.models.source import Source


class SupplierSyncing(Protocol):
    async def run_once(self) -> SyncResult:
        """Обходит все подключённые источники один раз."""

    async def run_forever(self) -> None:
        """Повторяет обход с интервалом из конфигурации."""


class SourceCatalog(Protocol):
    async def list_all(self) -> list[Source]: ...


class CrawlJournalReader(Protocol):
    async def last_runs(self, source_id: UUID, limit: int = 10) -> list[CrawlRun]: ...


class OfferEnriching(Protocol):
    async def run(self, limit: int | None = None) -> EnrichmentResult:
        """Пересчитывает нормализацию и классификацию сохранённых позиций."""


class OfferReidentifying(Protocol):
    async def run(self) -> ReidentifyResult:
        """Переводит сохранённые позиции на действующее правило ключа."""


class RegistryImporting(Protocol):
    async def run(self) -> RegistryImportResult:
        """Загружает выгрузку реестра МСП и удаляет выбывшие компании."""


class CoverageReading(Protocol):
    async def coverage(self) -> CoverageReport: ...


class SchemaMigrator(Protocol):
    async def apply_pending(self) -> list[str]: ...

    async def applied_names(self) -> list[str]: ...
