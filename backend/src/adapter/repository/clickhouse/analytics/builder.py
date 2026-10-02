import asyncio
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from src.adapter.repository.clickhouse.analytics import sql
from src.adapter.repository.clickhouse.analytics.mapping import (
    to_category,
    to_counts,
    to_problem,
    to_run,
    to_sources,
)
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.models.analytics.filters import DEFINITIONS_VERSION, AnalyticsFilters, FreshnessPolicy
from src.models.analytics.measure import Ratio
from src.models.analytics.records import RecordProblem
from src.models.analytics.slice import AnalyticsSlice, CategoryRow

TOTALS = (
    "SELECT count(), uniqExact(o.supplier_id), countIf({fresh}), countIf({unknown}), "
    "countIf({searchable}), countIf({commercial}), "
    "countIf({commercial} AND isNotNull(o.price)) {base}"
)
GROUPED = "SELECT {key} AS k, count() {base} GROUP BY k ORDER BY k"
CATEGORIES = (
    "SELECT {code} AS code, {parent} AS parent, count(), uniqExact(o.supplier_id), "
    "countIf({verified}), countIf({fresh}), countIf(isNotNull(o.price)), countIf({searchable}), "
    "countIf({system}), countIf({reported}) {base} {condition} "
    "GROUP BY code, parent ORDER BY count() DESC, code LIMIT {limit}"
)
SOURCE_OFFERS = (
    "SELECT o.source_id, count(), uniqExact(o.supplier_id), countIf({fresh}), countIf({unknown}), "
    "maxIf(o.last_seen_at, {known}) {base} GROUP BY o.source_id"
)
SOURCE_LIST = (
    "SELECT s.source_id, s.name, s.provider_name, s.source_type "
    "FROM {db}.sources_current AS s WHERE 1 {scope} ORDER BY s.name, s.source_id"
)
SOURCE_RUNS = (
    "SELECT r.source_id, maxIf(r.finished_at, r.status = 'success'), max(r.finished_at), "
    "argMax(r.status, r.finished_at), countIf(r.finished_at >= {{since:DateTime64(3)}}), "
    "countIf(r.status = 'failed' AND r.finished_at >= {{since:DateTime64(3)}}) "
    "FROM {db}.crawl_runs AS r FINAL INNER JOIN {db}.sources_current AS s "
    "ON s.source_id = r.source_id WHERE 1 {scope} GROUP BY r.source_id"
)
RUN_TOTALS = (
    "SELECT countIf(r.status = 'success'), count(), countIf(r.status = 'partial') "
    "FROM {db}.crawl_runs AS r FINAL INNER JOIN {db}.sources_current AS s "
    "ON s.source_id = r.source_id WHERE r.finished_at >= {{since:DateTime64(3)}} {scope}"
)
RECENT_RUNS = (
    "SELECT r.run_id, r.source_id, s.name, r.provider_name, r.started_at, r.finished_at, "
    "r.status, r.suppliers_extracted, r.offers_extracted, r.error_message "
    "FROM {db}.crawl_runs AS r FINAL INNER JOIN {db}.sources_current AS s "
    "ON s.source_id = r.source_id WHERE 1 {scope} "
    "ORDER BY r.finished_at DESC, r.run_id LIMIT {limit}"
)
PROBLEMS = (
    "SELECT o.source_id, any(s.name), count(), countIf({no_supplier}), countIf({unverified}), "
    "countIf({no_category}), countIf({no_price}), countIf({no_attributes}), countIf({stale}), "
    "countIf({unknown}) {base} GROUP BY o.source_id ORDER BY o.source_id"
)
CATEGORY_LIMIT = 2000
RUN_LIMIT = 50
CLASS_CODE = "if(length(o.okpd2_code) < 2, '', left(o.okpd2_code, 2))"
GROUP_CODE = "left(o.okpd2_code, 5)"


class ClickHouseSliceBuilder:
    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._db = database

    async def build(
        self,
        snapshot_id: UUID,
        filters: AnalyticsFilters,
        policy: FreshnessPolicy,
        as_of: datetime,
        computed_at: datetime,
    ) -> AnalyticsSlice:
        scope, parameters = sql.scope_of(filters)
        source_scope, source_parameters = sql.scope_of(filters, "s.source_id", region=False)
        run_scope, run_parameters = sql.scope_of(filters, "r.source_id", region=False)
        since = as_of - timedelta(days=policy.period_days)
        base = sql.BASE.format(db=self._db, scope=scope)
        values = {**parameters, **sql.policy_parameters(policy, as_of)}
        (
            totals,
            composition,
            age,
            availability,
            origins,
            classes,
            groups,
            source_offers,
            problems,
        ) = await asyncio.gather(
            self._select(self._totals(base), values),
            self._grouped(base, "toString(s.source_type)", values),
            self._grouped(base, sql.AGE_BUCKET, values),
            self._grouped(base, "toString(o.availability)", values),
            self._grouped(base, sql.ORIGIN, values),
            self._select(self._categories(base, CLASS_CODE, "''", ""), values),
            self._select(
                self._categories(
                    base, GROUP_CODE, "left(o.okpd2_code, 2)", "AND length(o.okpd2_code) >= 5"
                ),
                values,
            ),
            self._select(self._source_offers(base), values),
            self._select(self._problems(base), values),
        )
        sources, run_totals, runs = await asyncio.gather(
            self._select(SOURCE_LIST.format(db=self._db, scope=source_scope), source_parameters),
            self._select(
                RUN_TOTALS.format(db=self._db, scope=run_scope),
                {**run_parameters, "since": since},
            ),
            self._select(
                RECENT_RUNS.format(db=self._db, scope=run_scope, limit=RUN_LIMIT), run_parameters
            ),
        )
        attempts = await self._select(
            SOURCE_RUNS.format(db=self._db, scope=run_scope), {**run_parameters, "since": since}
        )
        total = totals[0]
        known = int(total[0]) - int(total[3])
        run_row = run_totals[0]
        return AnalyticsSlice(
            snapshot_id=snapshot_id,
            as_of=as_of,
            computed_at=computed_at,
            definitions_version=DEFINITIONS_VERSION,
            filters=filters,
            policy=policy,
            offers=int(total[0]),
            companies=int(total[1]),
            composition=to_counts(composition),
            fresh=Ratio(int(total[2]), known, int(total[3])),
            searchable=Ratio(int(total[4]), int(total[0])),
            priced=Ratio(int(total[6]), int(total[5])),
            runs_success=Ratio(int(run_row[0]), int(run_row[1])),
            runs_partial=int(run_row[2]),
            age=to_counts(age),
            availability=to_counts(availability),
            origins=to_counts(origins),
            categories=self._merged(classes, groups),
            sources=to_sources(sources, source_offers, attempts),
            runs=tuple(to_run(row) for row in runs),
            problems=tuple(to_problem(row) for row in problems),
        )

    def _totals(self, base: str) -> str:
        return TOTALS.format(
            fresh=sql.FRESH_KNOWN,
            unknown=sql.UNKNOWN_AGE,
            searchable=sql.SEARCHABLE,
            commercial=sql.COMMERCIAL,
            base=base,
        )

    async def _grouped(
        self, base: str, key: str, parameters: Mapping[str, Any]
    ) -> list[tuple[Any, ...]]:
        return await self._select(GROUPED.format(key=key, base=base), parameters)

    def _categories(self, base: str, code: str, parent: str, condition: str) -> str:
        return CATEGORIES.format(
            code=code,
            parent=parent,
            verified=sql.VERIFIED,
            fresh=sql.FRESH_KNOWN,
            searchable=sql.SEARCHABLE,
            system=sql.SYSTEM_ASSIGNED,
            reported=sql.SOURCE_REPORTED,
            base=base,
            condition=condition,
            limit=CATEGORY_LIMIT,
        )

    def _source_offers(self, base: str) -> str:
        return SOURCE_OFFERS.format(
            fresh=sql.FRESH_KNOWN, unknown=sql.UNKNOWN_AGE, known=sql.KNOWN, base=base
        )

    def _problems(self, base: str) -> str:
        return PROBLEMS.format(
            no_supplier=sql.PROBLEMS[RecordProblem.NO_SUPPLIER],
            unverified=sql.PROBLEMS[RecordProblem.UNVERIFIED_SELLER],
            no_category=sql.PROBLEMS[RecordProblem.NO_CATEGORY],
            no_price=sql.PROBLEMS[RecordProblem.NO_PRICE],
            no_attributes=sql.PROBLEMS[RecordProblem.NO_ATTRIBUTES],
            stale=sql.STALE,
            unknown=sql.UNKNOWN_AGE,
            base=base,
        )

    def _merged(
        self, classes: list[tuple[Any, ...]], groups: list[tuple[Any, ...]]
    ) -> tuple[CategoryRow, ...]:
        return tuple(to_category(row) for row in (*classes, *groups))

    async def _select(self, statement: str, parameters: Mapping[str, Any]) -> list[tuple[Any, ...]]:
        return await self._gateway.select(statement, parameters)
