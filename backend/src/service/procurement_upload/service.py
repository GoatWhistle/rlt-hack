import logging
from collections.abc import Sequence
from uuid import UUID

from src.models.errors import NoValidLotsError
from src.models.upload import (
    LotDetail,
    PendingLot,
    ProcessedLot,
    Upload,
    UploadDetail,
    UploadResults,
    UploadSummary,
)
from src.service.errors import LotNotFoundError, UploadNotFoundError, UploadQueueFullError
from src.service.procurement_upload.protocols import (
    Clock,
    IdGenerator,
    LotQueue,
    NoticeReader,
    UploadStore,
)
from src.service.procurement_upload.settings import UploadSettings

logger = logging.getLogger(__name__)


class ProcurementUploadService:
    def __init__(
        self,
        reader: NoticeReader,
        store: UploadStore,
        runner: LotQueue,
        clock: Clock,
        ids: IdGenerator,
        settings: UploadSettings,
    ) -> None:
        self._reader = reader
        self._store = store
        self._runner = runner
        self._clock = clock
        self._ids = ids
        self._settings = settings

    async def start(self) -> None:
        await self._runner.start()

    async def stop(self) -> None:
        await self._runner.stop()

    async def upload(self, file_name: str, content: bytes) -> UploadSummary:
        notices = await self._reader.read(content, self._settings.max_rows)
        if not notices.lots:
            raise NoValidLotsError
        if self._runner.backlog + len(notices.lots) > self._settings.max_backlog:
            raise UploadQueueFullError(self._settings.max_backlog)
        upload = Upload.of(self._ids.new(), file_name, self._clock.now(), notices)
        await self._store.create(upload, notices.lots)
        self._runner.submit([PendingLot(upload.upload_id, lot) for lot in notices.lots])
        logger.info(
            "upload accepted",
            extra={
                "upload_id": str(upload.upload_id),
                "lots": upload.total,
                "rejected": upload.rejected,
            },
        )
        return UploadSummary(upload)

    async def recent(self, limit: int) -> tuple[UploadSummary, ...]:
        return await self._store.recent(limit)

    async def summary(self, upload_id: UUID) -> UploadSummary:
        summary = await self._store.summary(upload_id)
        if summary is None:
            raise UploadNotFoundError(upload_id)
        return summary

    async def get(self, upload_id: UUID) -> UploadDetail:
        detail = await self._store.detail(upload_id)
        if detail is None:
            raise UploadNotFoundError(upload_id)
        return detail

    async def lot(self, upload_id: UUID, lot_id: str) -> LotDetail:
        detail = await self._store.lot(upload_id, lot_id)
        if detail is None:
            if await self._store.summary(upload_id) is None:
                raise UploadNotFoundError(upload_id)
            raise LotNotFoundError(upload_id, lot_id)
        return detail

    async def results(self, upload_id: UUID, lot_ids: Sequence[str]) -> UploadResults:
        summary = await self._store.summary(upload_id)
        if summary is None:
            raise UploadNotFoundError(upload_id)
        wanted = tuple(dict.fromkeys(lot_ids))[: self._settings.max_selected_lots]
        if not wanted:
            return UploadResults(summary)
        found = await self._store.results(upload_id, wanted)
        return UploadResults(summary, _ordered(found, wanted))


def _ordered(found: Sequence[ProcessedLot], wanted: Sequence[str]) -> tuple[ProcessedLot, ...]:
    order = {lot_id: position for position, lot_id in enumerate(wanted)}
    kept = (entry for entry in found if not entry.result.failed)
    return tuple(sorted(kept, key=lambda entry: order.get(entry.result.lot_id, len(order))))
