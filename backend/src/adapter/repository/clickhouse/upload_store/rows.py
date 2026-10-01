from collections.abc import Sequence
from datetime import date
from typing import Any
from uuid import UUID

from src.adapter.repository.clickhouse.rows import to_datetime, to_decimal, to_uuid
from src.adapter.repository.clickhouse.upload_store.codec import decode_issues, encode_issues
from src.adapter.repository.clickhouse.versions import event_version
from src.models.enums import LotStatus
from src.models.procurement import ProcurementLot
from src.models.upload import LotProgress, PendingLot, Upload

type Row = Sequence[Any]


def upload_row(upload: Upload) -> tuple[Any, ...]:
    return (
        upload.upload_id,
        upload.file_name,
        upload.total,
        upload.rejected,
        encode_issues(upload.issues),
        upload.created_at,
        event_version(upload.created_at),
        0,
    )


def lot_row(upload: Upload, position: int, lot: ProcurementLot) -> tuple[Any, ...]:
    return (
        upload.upload_id,
        lot.lot_id,
        position,
        lot.row,
        lot.title,
        lot.subject,
        lot.customer_inn,
        "" if lot.publish_date is None else lot.publish_date.isoformat(),
        lot.start_price,
        upload.created_at,
        event_version(upload.created_at),
        0,
    )


def to_upload(row: Row) -> Upload:
    return Upload(
        upload_id=to_uuid(row[0]),
        file_name=str(row[1]),
        total=int(str(row[2])),
        issues=decode_issues(str(row[3] or "")),
        created_at=to_datetime(row[4]),
    )


def to_lot(row: Row) -> ProcurementLot:
    published = str(row[5] or "")
    return ProcurementLot(
        lot_id=str(row[0]),
        row=int(str(row[1])),
        title=str(row[2]),
        subject=str(row[3] or ""),
        customer_inn=str(row[4] or ""),
        publish_date=date.fromisoformat(published) if published else None,
        start_price=to_decimal(row[6]),
    )


def to_pending(row: Row) -> PendingLot:
    return PendingLot(upload_id=to_uuid(row[0]), lot=to_lot(row[1:]))


def to_progress(lot: ProcurementLot, state: Row | None) -> LotProgress:
    if state is None:
        return LotProgress(lot)
    return LotProgress(lot, LotStatus(str(state[1])), int(str(state[2])), int(str(state[3])))


def statuses_by_upload(rows: Sequence[Row]) -> dict[UUID, list[LotStatus]]:
    grouped: dict[UUID, list[LotStatus]] = {}
    for row in rows:
        status = LotStatus(str(row[1]))
        grouped.setdefault(to_uuid(row[0]), []).extend([status] * int(str(row[2])))
    return grouped
