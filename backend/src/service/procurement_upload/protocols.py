from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.models.lot_result import LotResult
from src.models.procurement import NoticeFile, ProcurementLot
from src.models.search import SearchQuery
from src.models.search_result import SearchResult
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
    async def search(self, query: SearchQuery) -> SearchResult: ...


class SearchReading(Protocol):
    async def get(self, search_id: UUID) -> SearchResult | None: ...


class LotProcessing(Protocol):
    async def process(self, lot: ProcurementLot) -> LotResult: ...


class UploadStore(Protocol):
    async def create(self, upload: Upload, lots: Sequence[ProcurementLot]) -> None: ...

    async def recent(self, owner: str, limit: int) -> tuple[UploadSummary, ...]: ...

    async def summary(self, owner: str, upload_id: UUID) -> UploadSummary | None: ...

    async def detail(self, owner: str, upload_id: UUID) -> UploadDetail | None: ...

    async def lot(self, owner: str, upload_id: UUID, lot_id: str) -> LotDetail | None: ...

    async def results(
        self, owner: str, upload_id: UUID, lot_ids: Sequence[str]
    ) -> tuple[ProcessedLot, ...]: ...


class PendingLots(Protocol):
    async def pending(self) -> tuple[PendingLot, ...]: ...

    async def save_result(self, upload_id: UUID, result: LotResult) -> None: ...


class LotQueue(Protocol):
    @property
    def backlog(self) -> int: ...

    def submit(self, lots: Sequence[PendingLot]) -> None: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new(self) -> UUID: ...
