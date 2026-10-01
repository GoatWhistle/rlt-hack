"""Журнал обхода источников и итоги синхронизации."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.models.enums import FetchStatus


@dataclass(frozen=True, slots=True)
class CrawlRun:
    """Завершённый обход одного источника одним адаптером."""

    run_id: UUID
    source_id: UUID
    started_at: datetime
    finished_at: datetime
    status: FetchStatus
    suppliers_extracted: int
    offers_extracted: int
    provider_name: str
    error_message: str = ""


@dataclass(frozen=True, slots=True)
class SourceSyncResult:
    """Итог обхода одного источника."""

    provider_name: str
    status: FetchStatus
    source_id: UUID | None = None
    suppliers_extracted: int = 0
    offers_extracted: int = 0
    offers_withdrawn: int = 0
    error_message: str = ""


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Итог обхода всех подключённых источников."""

    sources: tuple[SourceSyncResult, ...] = ()

    @property
    def failed(self) -> int:
        return sum(1 for item in self.sources if item.status == FetchStatus.FAILED)

    @property
    def suppliers_extracted(self) -> int:
        return sum(item.suppliers_extracted for item in self.sources)

    @property
    def offers_extracted(self) -> int:
        return sum(item.offers_extracted for item in self.sources)
