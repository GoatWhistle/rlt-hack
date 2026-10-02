from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.models.upload import LotDetail, UploadDetail, UploadResults, UploadSummary


class ProcurementUploads(Protocol):
    async def upload(self, owner: str, file_name: str, content: bytes) -> UploadSummary: ...

    async def recent(self, owner: str, limit: int) -> tuple[UploadSummary, ...]: ...

    async def summary(self, owner: str, upload_id: UUID) -> UploadSummary: ...

    async def get(self, owner: str, upload_id: UUID) -> UploadDetail: ...

    async def lot(self, owner: str, upload_id: UUID, lot_id: str) -> LotDetail: ...

    async def results(
        self, owner: str, upload_id: UUID, lot_ids: Sequence[str]
    ) -> UploadResults: ...
