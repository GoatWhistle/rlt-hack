import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from uuid import UUID

from src.models.enums import WarningCode
from src.models.lot_result import LotResult
from src.models.procurement import NoticeFile, ProcurementLot
from src.models.search import SearchQuery
from src.models.search_result import SearchResult, SearchWarning
from src.models.upload import (
    LotDetail,
    LotProgress,
    PendingLot,
    ProcessedLot,
    StatusCounts,
    Upload,
    UploadDetail,
    UploadSummary,
)
from src.service.errors import UninterpretableQueryError
from tests.fakes.domain import MOMENT
from tests.fakes.ports import PortFailureError


@dataclass(slots=True)
class FakeReader:
    notices: NoticeFile
    error: Exception | None = None
    calls: list[tuple[bytes, int]] = field(default_factory=list)

    async def read(self, content: bytes, max_rows: int) -> NoticeFile:
        self.calls.append((content, max_rows))
        if self.error is not None:
            raise self.error
        return self.notices


@dataclass(slots=True)
class FakeLotSearch:
    result: SearchResult | None
    delay: float = 0.0
    unarchived: bool = False
    queries: list[SearchQuery] = field(default_factory=list)

    async def search(self, query: SearchQuery) -> SearchResult:
        self.queries.append(query)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.result is None:
            raise UninterpretableQueryError
        if self.unarchived:
            warning = SearchWarning(WarningCode.ARCHIVE_FAILED)
            return replace(self.result, warnings=(*self.result.warnings, warning))
        return self.result


@dataclass(slots=True)
class FakeSearchReading:
    searches: dict[UUID, SearchResult] = field(default_factory=dict)

    async def get(self, search_id: UUID) -> SearchResult | None:
        return self.searches.get(search_id)


@dataclass(slots=True)
class FakeProcessor:
    failures: dict[str, int] = field(default_factory=dict)
    errors: dict[str, Exception] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)
    gate: asyncio.Event | None = None

    async def process(self, lot: ProcurementLot) -> LotResult:
        self.calls.append(lot.lot_id)
        if self.gate is not None:
            await self.gate.wait()
        if lot.lot_id in self.errors:
            raise self.errors[lot.lot_id]
        remaining = self.failures.get(lot.lot_id, 0)
        if remaining:
            self.failures[lot.lot_id] = remaining - 1
            raise PortFailureError(lot.lot_id)
        return LotResult(lot_id=lot.lot_id, processed_at=MOMENT)


@dataclass(slots=True)
class MemoryUploadStore:
    uploads: dict[UUID, Upload] = field(default_factory=dict)
    lots: dict[UUID, list[ProcurementLot]] = field(default_factory=dict)
    saved: dict[tuple[UUID, str], LotResult] = field(default_factory=dict)
    failing_saves: int = 0
    failing_pending: int = 0

    async def create(self, upload: Upload, lots: Sequence[ProcurementLot]) -> None:
        self.uploads[upload.upload_id] = upload
        self.lots[upload.upload_id] = list(lots)

    async def save_result(self, upload_id: UUID, result: LotResult) -> None:
        if self.failing_saves:
            self.failing_saves -= 1
            raise PortFailureError("save")
        self.saved[(upload_id, result.lot_id)] = result

    async def recent(self, owner: str, limit: int) -> tuple[UploadSummary, ...]:
        summaries = [
            self._summary(upload_id)
            for upload_id, upload in self.uploads.items()
            if upload.owner == owner
        ]
        return tuple(summaries[:limit])

    async def summary(self, owner: str, upload_id: UUID) -> UploadSummary | None:
        return self._summary(upload_id) if self._owns(owner, upload_id) else None

    async def detail(self, owner: str, upload_id: UUID) -> UploadDetail | None:
        if not self._owns(owner, upload_id):
            return None
        lots = tuple(self._progress(upload_id, lot) for lot in self.lots[upload_id])
        return UploadDetail(self._summary(upload_id), lots)

    async def lot(self, owner: str, upload_id: UUID, lot_id: str) -> LotDetail | None:
        if not self._owns(owner, upload_id):
            return None
        found = [lot for lot in self.lots.get(upload_id, []) if lot.lot_id == lot_id]
        if not found:
            return None
        result = self.saved.get((upload_id, lot_id))
        return LotDetail(self._summary(upload_id), self._progress(upload_id, found[0]), result)

    async def results(
        self, owner: str, upload_id: UUID, lot_ids: Sequence[str]
    ) -> tuple[ProcessedLot, ...]:
        if not self._owns(owner, upload_id):
            return ()
        wanted = set(lot_ids)
        return tuple(
            ProcessedLot(self._progress(upload_id, lot), self.saved[(upload_id, lot.lot_id)])
            for lot in self.lots.get(upload_id, [])
            if lot.lot_id in wanted and (upload_id, lot.lot_id) in self.saved
        )

    async def pending(self) -> tuple[PendingLot, ...]:
        if self.failing_pending:
            self.failing_pending -= 1
            raise PortFailureError("pending")
        return tuple(
            PendingLot(upload_id, lot)
            for upload_id, lots in self.lots.items()
            for lot in lots
            if (upload_id, lot.lot_id) not in self.saved
        )

    def _owns(self, owner: str, upload_id: UUID) -> bool:
        upload = self.uploads.get(upload_id)
        return upload is not None and upload.owner == owner

    def _progress(self, upload_id: UUID, lot: ProcurementLot) -> LotProgress:
        return LotProgress.of(lot, self.saved.get((upload_id, lot.lot_id)))

    def _summary(self, upload_id: UUID) -> UploadSummary:
        statuses = [
            result.status for (owner, _), result in self.saved.items() if owner == upload_id
        ]
        return UploadSummary(self.uploads[upload_id], StatusCounts.tally(statuses))
