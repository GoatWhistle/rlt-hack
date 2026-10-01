from collections.abc import Mapping, Sequence
from uuid import UUID

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.supplier_read.mapping import SUPPLIER_COLUMNS, to_supplier
from src.models.supplier import Supplier

SELECT_SUPPLIERS = (
    "SELECT {columns} FROM {db}.suppliers_current WHERE supplier_id IN {{ids:Array(UUID)}}"
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
        suppliers = (to_supplier(row) for row in rows)
        return {supplier.supplier_id: supplier for supplier in suppliers}
