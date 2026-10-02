from collections.abc import Mapping, Sequence
from uuid import UUID

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.supplier_read.mapping import SUPPLIER_COLUMNS, to_supplier
from src.models.supplier import Supplier, operator_host

SELECT_SUPPLIERS = (
    "SELECT {columns} FROM {db}.suppliers_current WHERE supplier_id IN {{ids:Array(UUID)}}"
)
SELECT_OPERATORS = (
    "SELECT DISTINCT base_url FROM {db}.sources_current "
    "WHERE source_type IN ('directory', 'registry', 'dataset')"
)


class ClickHouseSupplierDirectory:
    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._db = database

    async def get_many(self, supplier_ids: Sequence[UUID]) -> Mapping[UUID, Supplier]:
        unique = list(dict.fromkeys(supplier_ids))
        if not unique:
            return {}
        statement = SELECT_SUPPLIERS.format(columns=", ".join(SUPPLIER_COLUMNS), db=self._db)
        rows = await self._gateway.select(statement, {"ids": [str(item) for item in unique]})
        operators = await self._operators()
        suppliers = (to_supplier(row).without_operator_contacts(operators) for row in rows)
        return {supplier.supplier_id: supplier for supplier in suppliers}

    async def _operators(self) -> frozenset[str]:
        rows = await self._gateway.select(SELECT_OPERATORS.format(db=self._db))
        hosts = (operator_host(str(row[0] or "")) for row in rows)
        return frozenset(host for host in hosts if host)
