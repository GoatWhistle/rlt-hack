from collections.abc import Mapping, Sequence
from dataclasses import replace
from uuid import UUID

from src.adapter.repository.clickhouse.catalog.supplier_read.mapping import (
    SUPPLIER_COLUMNS,
    to_supplier,
)
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.models.catalog.supplier import Supplier

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
        suppliers = [to_supplier(row) for row in rows]
        inns = [supplier.inn for supplier in suppliers if supplier.inn]
        regions = {}
        if inns:
            regions = dict(
                await self._gateway.select(
                    f"SELECT inn, region FROM {self._db}.msp_companies FINAL "
                    "WHERE inn IN {inns:Array(String)} AND region != ''",
                    {"inns": inns},
                )
            )
        suppliers = [
            replace(supplier, registered_region=regions.get(supplier.inn, ""))
            for supplier in suppliers
        ]
        return {supplier.supplier_id: supplier for supplier in suppliers}
