from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.models.lot_result import LotResult
from src.models.match import MatchReport
from src.models.procurement import NoticeFile, ProcurementLot
from src.models.search import SearchQuery
from src.models.upload import (
    LotDetail,
    PendingLot,
    ProcessedLot,
    Upload,
    UploadDetail,
    UploadSummary,
)


class NoticeReader(Protocol):
    async def read(self, content: bytes, max_rows: int) -> NoticeFile: ...


class LotSearching(Protocol):
    async def run(self, query: SearchQuery) -> MatchReport: ...


class LotProcessing(Protocol):
    async def process(self, lot: ProcurementLot) -> LotResult: ...


class UploadStore(Protocol):
    async def create(self, upload: Upload, lots: Sequence[ProcurementLot]) -> None: ...

    async def save_result(self, upload_id: UUID, result: LotResult) -> None: ...

    async def recent(self, limit: int) -> tuple[UploadSummary, ...]: ...

    async def summary(self, upload_id: UUID) -> UploadSummary | None: ...

    async def detail(self, upload_id: UUID) -> UploadDetail | None: ...

    async def lot(self, upload_id: UUID, lot_id: str) -> LotDetail | None: ...

    async def results(
        self, upload_id: UUID, lot_ids: Sequence[str]
    ) -> tuple[ProcessedLot, ...]: ...

    async def pending(self) -> tuple[PendingLot, ...]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new(self) -> UUID: ...
