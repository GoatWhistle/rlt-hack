from collections.abc import Sequence
from typing import Any
from uuid import UUID

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.upload_store.codec import (
    decode_lot_result,
    encode_lot_result,
)
from src.adapter.repository.clickhouse.upload_store.query import (
    LOT_COLUMNS,
    RESULT_COLUMNS,
    SELECT_CHOSEN_LOTS,
    SELECT_COUNTS,
    SELECT_LOTS,
    SELECT_PAYLOADS,
    SELECT_PENDING,
    SELECT_RECENT,
    SELECT_STATES,
    SELECT_UPLOAD,
    UPLOAD_COLUMNS,
)
from src.adapter.repository.clickhouse.upload_store.rows import (
    lot_row,
    statuses_by_upload,
    to_lot,
    to_pending,
    to_progress,
    to_upload,
    upload_row,
)
from src.adapter.repository.clickhouse.versions import event_version
from src.models.lot_result import LotResult
from src.models.procurement import ProcurementLot
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

LOT_BATCH = 500


def batches(values: Sequence[str]) -> list[list[str]]:
    return [list(values[start : start + LOT_BATCH]) for start in range(0, len(values), LOT_BATCH)]


class ClickHouseUploadStore:
    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._db = database

    async def create(self, upload: Upload, lots: Sequence[ProcurementLot]) -> None:
        rows = [lot_row(upload, position, lot) for position, lot in enumerate(lots)]
        await self._gateway.insert(f"{self._db}.upload_lots", LOT_COLUMNS, rows)
        await self._gateway.insert(f"{self._db}.uploads", UPLOAD_COLUMNS, [upload_row(upload)])

    async def save_result(self, upload_id: UUID, result: LotResult) -> None:
        row = (
            upload_id,
            result.lot_id,
            str(result.status),
            len(result.items),
            len(result.candidates),
            encode_lot_result(result),
            result.processed_at,
            event_version(result.processed_at),
            0,
        )
        await self._gateway.insert(f"{self._db}.upload_results", RESULT_COLUMNS, [row])

    async def recent(self, limit: int) -> tuple[UploadSummary, ...]:
        if limit < 1:
            return ()
        rows = await self._gateway.select(SELECT_RECENT.format(db=self._db), {"limit": limit})
        return await self._summaries([to_upload(row) for row in rows])

    async def summary(self, upload_id: UUID) -> UploadSummary | None:
        rows = await self._by_upload(SELECT_UPLOAD, upload_id)
        if not rows:
            return None
        return (await self._summaries([to_upload(rows[0])]))[0]

    async def detail(self, upload_id: UUID) -> UploadDetail | None:
        summary = await self.summary(upload_id)
        if summary is None:
            return None
        lots = await self._by_upload(SELECT_LOTS, upload_id)
        states = {str(row[0]): row for row in await self._by_upload(SELECT_STATES, upload_id)}
        progress = tuple(to_progress(lot, states.get(lot.lot_id)) for lot in map(to_lot, lots))
        return UploadDetail(summary=summary, lots=progress)

    async def lot(self, upload_id: UUID, lot_id: str) -> LotDetail | None:
        summary = await self.summary(upload_id)
        if summary is None:
            return None
        lots = await self._chosen_lots(upload_id, [lot_id])
        if not lots:
            return None
        result = (await self._payloads(upload_id, [lot_id])).get(lot_id)
        return LotDetail(summary, LotProgress.of(lots[0], result), result)

    async def results(self, upload_id: UUID, lot_ids: Sequence[str]) -> tuple[ProcessedLot, ...]:
        lots = await self._chosen_lots(upload_id, lot_ids)
        payloads = await self._payloads(upload_id, lot_ids)
        return tuple(
            ProcessedLot(LotProgress.of(lot, payloads[lot.lot_id]), payloads[lot.lot_id])
            for lot in lots
            if lot.lot_id in payloads
        )

    async def pending(self) -> tuple[PendingLot, ...]:
        rows = await self._gateway.select(SELECT_PENDING.format(db=self._db))
        return tuple(to_pending(row) for row in rows)

    async def _summaries(self, uploads: Sequence[Upload]) -> tuple[UploadSummary, ...]:
        if not uploads:
            return ()
        ids = [str(upload.upload_id) for upload in uploads]
        rows = await self._gateway.select(SELECT_COUNTS.format(db=self._db), {"ids": ids})
        statuses = statuses_by_upload(rows)
        return tuple(
            UploadSummary(upload, StatusCounts.tally(statuses.get(upload.upload_id, ())))
            for upload in uploads
        )

    async def _by_upload(self, statement: str, upload_id: UUID) -> list[tuple[Any, ...]]:
        return await self._gateway.select(
            statement.format(db=self._db), {"upload_id": str(upload_id)}
        )

    async def _chosen_lots(self, upload_id: UUID, lot_ids: Sequence[str]) -> list[ProcurementLot]:
        found: list[ProcurementLot] = []
        for batch in batches(lot_ids):
            rows = await self._gateway.select(
                SELECT_CHOSEN_LOTS.format(db=self._db),
                {"upload_id": str(upload_id), "lot_ids": batch},
            )
            found.extend(to_lot(row) for row in rows)
        return found

    async def _payloads(self, upload_id: UUID, lot_ids: Sequence[str]) -> dict[str, LotResult]:
        found: dict[str, LotResult] = {}
        for batch in batches(lot_ids):
            rows = await self._gateway.select(
                SELECT_PAYLOADS.format(db=self._db),
                {"upload_id": str(upload_id), "lot_ids": batch},
            )
            found.update((str(row[0]), decode_lot_result(str(row[1]))) for row in rows)
        return found
