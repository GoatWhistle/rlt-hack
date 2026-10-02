from collections.abc import Mapping, Sequence
from uuid import UUID

from src.adapter.repository.clickhouse.engine.rows import to_uuid
from src.adapter.repository.clickhouse.protocols import SqlGateway

SELECT_BY_INN = (
    "SELECT inn, groupUniqArray(2)(supplier_id) FROM {db}.suppliers_current "
    "WHERE inn IN {{inns:Array(String)}} GROUP BY inn"
)


class ClickHouseSupplierIdentity:
    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._db = database

    async def ids_by_inn(self, inns: Sequence[str]) -> Mapping[str, UUID]:
        unique = list(dict.fromkeys(inn.strip() for inn in inns if inn.strip()))
        if not unique:
            return {}
        rows = await self._gateway.select(SELECT_BY_INN.format(db=self._db), {"inns": unique})
        return {
            str(inn): to_uuid(identifiers[0])
            for inn, identifiers in rows
            if isinstance(identifiers, list) and len(identifiers) == 1
        }
