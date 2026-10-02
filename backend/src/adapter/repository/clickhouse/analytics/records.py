from datetime import datetime
from typing import Any

from src.adapter.repository.clickhouse.analytics import sql
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.rows import (
    to_datetime,
    to_decimal,
    to_optional_uuid,
    to_uuid,
)
from src.models.analytics.filters import AnalyticsFilters, FreshnessPolicy
from src.models.analytics.records import RecordPage, RecordQuery, RecordRow

COUNT = "SELECT count(), countIf(o.updated_at > {{as_of:DateTime64(3)}}) {base} {condition}"
PAGE = (
    "SELECT o.offer_id, o.name, o.source_id, s.name, o.supplier_id, c.name, o.okpd2_code, "
    "o.price, o.currency, o.url, o.last_seen_at, o.updated_at {base} {condition} "
    "ORDER BY o.last_seen_at DESC, o.offer_id LIMIT {{limit:UInt32}} OFFSET {{offset:UInt32}}"
)


class ClickHouseRecordReader:
    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._db = database

    async def page(
        self,
        filters: AnalyticsFilters,
        query: RecordQuery,
        policy: FreshnessPolicy,
        as_of: datetime,
    ) -> RecordPage:
        scope, parameters = sql.scope_of(filters)
        base = sql.BASE.format(db=self._db, scope=scope)
        condition, extra = self._condition(query)
        values: dict[str, Any] = {
            **parameters,
            **extra,
            **sql.policy_parameters(policy, as_of),
            "limit": query.limit,
            "offset": query.offset,
        }
        counted = await self._gateway.select(COUNT.format(base=base, condition=condition), values)
        rows = await self._gateway.select(PAGE.format(base=base, condition=condition), values)
        return RecordPage(
            as_of=as_of,
            total=int(counted[0][0]),
            changed_after=int(counted[0][1]),
            items=tuple(self._record(row) for row in rows),
        )

    def _condition(self, query: RecordQuery) -> tuple[str, dict[str, Any]]:
        clauses: list[str] = []
        parameters: dict[str, Any] = {}
        if query.category:
            clauses.append("startsWith(o.okpd2_code, {category:String})")
            parameters["category"] = query.category
        if query.problem is not None:
            clauses.append(sql.PROBLEMS[query.problem])
        return "".join(f" AND {clause}" for clause in clauses), parameters

    def _record(self, row: tuple[Any, ...]) -> RecordRow:
        return RecordRow(
            offer_id=to_uuid(row[0]),
            name=str(row[1]),
            source_id=to_uuid(row[2]),
            source_name=str(row[3]),
            supplier_id=to_optional_uuid(row[4]),
            supplier_name=str(row[5]),
            okpd2_code=str(row[6]),
            price=to_decimal(row[7]),
            currency=str(row[8]),
            url=str(row[9]),
            last_seen_at=to_datetime(row[10]),
            updated_at=to_datetime(row[11]),
        )
