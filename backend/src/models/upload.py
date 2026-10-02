import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Self
from uuid import UUID

from src.models.enums import LotStatus
from src.models.errors import InvalidUploadError
from src.models.lot_result import LotResult
from src.models.procurement import NoticeFile, ProcurementLot, RowIssue
from src.models.search_result import SearchResult

FILE_NAME_MAX_LENGTH = 255
PATH_SEPARATORS = re.compile(r"[\\/]")
OWNER_PATTERN = re.compile(r"[0-9a-f]{32}")


def base_name(raw: str) -> str:
    return " ".join(PATH_SEPARATORS.split(raw)[-1].split())[:FILE_NAME_MAX_LENGTH]


@dataclass(frozen=True, slots=True)
class Upload:
    upload_id: UUID
    file_name: str
    created_at: datetime
    total: int
    issues: tuple[RowIssue, ...] = ()
    owner: str = ""

    def __post_init__(self) -> None:
        if self.owner and not OWNER_PATTERN.fullmatch(self.owner):
            raise InvalidUploadError("owner has a wrong format")
        name = base_name(self.file_name)
        if not name:
            raise InvalidUploadError("file name is empty")
        if self.created_at.tzinfo is None:
            raise InvalidUploadError("created_at must carry a timezone")
        if self.total < 1:
            raise InvalidUploadError("an upload has at least one lot")
        object.__setattr__(self, "file_name", name)

    @classmethod
    def of(
        cls,
        upload_id: UUID,
        file_name: str,
        created_at: datetime,
        file: NoticeFile,
        owner: str = "",
    ) -> Self:
        return cls(upload_id, file_name, created_at, len(file.lots), file.issues, owner)

    @property
    def rejected(self) -> int:
        return len({issue.row for issue in self.issues})


@dataclass(frozen=True, slots=True)
class LotProgress:
    lot: ProcurementLot
    status: LotStatus = LotStatus.QUEUED
    products: int = 0
    candidates: int = 0
    search_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.products < 0 or self.candidates < 0:
            raise InvalidUploadError("counters cannot be negative")

    @classmethod
    def of(cls, lot: ProcurementLot, result: LotResult | None) -> Self:
        if result is None:
            return cls(lot)
        return cls(lot, result.status, result.products, result.candidates, result.search_id)


@dataclass(frozen=True, slots=True)
class StatusCounts:
    ready: int = 0
    needs_check: int = 0
    no_candidates: int = 0
    failed: int = 0

    def __post_init__(self) -> None:
        if min(self.ready, self.needs_check, self.no_candidates, self.failed) < 0:
            raise InvalidUploadError("counters cannot be negative")

    @classmethod
    def tally(cls, statuses: Iterable[LotStatus]) -> Self:
        seen = list(statuses)
        return cls(
            ready=seen.count(LotStatus.READY),
            needs_check=seen.count(LotStatus.NEEDS_CHECK),
            no_candidates=seen.count(LotStatus.NO_CANDIDATES),
            failed=seen.count(LotStatus.FAILED),
        )

    @property
    def processed(self) -> int:
        return self.ready + self.needs_check + self.no_candidates + self.failed


@dataclass(frozen=True, slots=True)
class UploadSummary:
    upload: Upload
    counts: StatusCounts = field(default_factory=StatusCounts)

    def __post_init__(self) -> None:
        if self.counts.processed > self.upload.total:
            raise InvalidUploadError("more lots processed than uploaded")

    @property
    def processed(self) -> int:
        return self.counts.processed

    @property
    def finished(self) -> bool:
        return self.processed == self.upload.total


@dataclass(frozen=True, slots=True)
class UploadDetail:
    summary: UploadSummary
    lots: tuple[LotProgress, ...]


@dataclass(frozen=True, slots=True)
class LotDetail:
    summary: UploadSummary
    progress: LotProgress
    result: LotResult | None = None
    search: SearchResult | None = None


@dataclass(frozen=True, slots=True)
class PendingLot:
    upload_id: UUID
    lot: ProcurementLot

    @property
    def key(self) -> tuple[UUID, str]:
        return self.upload_id, self.lot.lot_id


@dataclass(frozen=True, slots=True)
class ProcessedLot:
    progress: LotProgress
    result: LotResult
    search: SearchResult | None = None

    def __post_init__(self) -> None:
        if self.progress.lot.lot_id != self.result.lot_id:
            raise InvalidUploadError("result belongs to another lot")
        if self.search is not None and self.search.search_id != self.result.search_id:
            raise InvalidUploadError("search belongs to another result")


@dataclass(frozen=True, slots=True)
class UploadResults:
    summary: UploadSummary
    lots: tuple[ProcessedLot, ...] = ()
