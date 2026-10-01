"""Репозиторий источников данных."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.rows import to_optional_uuid, to_uuid
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.models.enums import SourceType, VerificationStatus
from src.models.source import Source

COLUMNS = (
    "source_id",
    "name",
    "base_url",
    "source_type",
    "supplier_id",
    "ownership_status",
    "ownership_evidence_url",
    "provider_name",
    "enabled",
    "updated_at",
    "version",
    "is_deleted",
)

_SELECT = (
    "SELECT source_id, name, base_url, source_type, supplier_id, ownership_status, "
    "ownership_evidence_url, provider_name "
    "FROM {db}.sources_current"
)


class ClickHouseSourceRepository:
    def __init__(
        self,
        gateway: SqlGateway,
        versions: VersionSequencer,
        database: str = "supplier_search",
    ) -> None:
        self._gateway = gateway
        self._versions = versions
        self._db = database

    async def get(self, source_id: UUID) -> Source | None:
        rows = await self._gateway.select(
            _SELECT.format(db=self._db) + " WHERE source_id = {source_id:UUID}",
            {"source_id": str(source_id)},
        )
        return _to_source(rows[0]) if rows else None

    async def list_all(self) -> list[Source]:
        rows = await self._gateway.select(_SELECT.format(db=self._db) + " ORDER BY name")
        return [_to_source(row) for row in rows]

    async def save_many(self, sources: Sequence[Source]) -> None:
        updated_at = datetime.now(UTC)
        await self._gateway.insert(
            f"{self._db}.sources",
            COLUMNS,
            [
                (
                    source.source_id,
                    source.name,
                    source.base_url,
                    str(source.source_type),
                    source.supplier_id,
                    str(source.ownership_status),
                    source.ownership_evidence_url,
                    source.provider_name,
                    # Источник включается флагом адаптера, в таблице он всегда активен.
                    1,
                    updated_at,
                    self._versions.next(),
                    0,
                )
                for source in sources
            ],
        )


def _to_source(row: Sequence[object]) -> Source:
    return Source(
        source_id=to_uuid(row[0]),
        name=str(row[1]),
        base_url=str(row[2]),
        source_type=SourceType(str(row[3])),
        supplier_id=to_optional_uuid(row[4]),
        ownership_status=VerificationStatus(str(row[5])),
        ownership_evidence_url=str(row[6]),
        provider_name=str(row[7]),
    )
