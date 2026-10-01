"""Репозиторий компаний-поставщиков."""

from collections.abc import Sequence
from datetime import UTC, datetime

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.models.supplier import Supplier

COLUMNS = (
    "supplier_id",
    "inn",
    "kpps",
    "name",
    "region",
    "website",
    "contacts",
    "okved_codes",
    "identity_status",
    "identity_evidence_url",
    "updated_at",
    "version",
    "is_deleted",
)


class ClickHouseSupplierRepository:
    """Обновление — полный снимок строки новой версией."""

    def __init__(
        self,
        gateway: SqlGateway,
        versions: VersionSequencer,
        database: str = "supplier_search",
    ) -> None:
        self._gateway = gateway
        self._versions = versions
        self._db = database

    async def save_many(self, suppliers: Sequence[Supplier]) -> None:
        updated_at = datetime.now(UTC)
        await self._gateway.insert(
            f"{self._db}.suppliers",
            COLUMNS,
            [
                (
                    supplier.supplier_id,
                    supplier.inn,
                    list(supplier.kpps),
                    supplier.name,
                    supplier.region,
                    supplier.website,
                    dict(supplier.contacts),
                    list(supplier.okved_codes),
                    str(supplier.identity_status),
                    supplier.identity_evidence_url,
                    updated_at,
                    self._versions.next(),
                    0,
                )
                for supplier in suppliers
            ],
        )
