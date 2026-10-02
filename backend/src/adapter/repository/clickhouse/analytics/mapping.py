from collections.abc import Sequence
from datetime import datetime
from typing import Any

from src.adapter.repository.clickhouse.rows import to_datetime, to_uuid
from src.models.analytics.measure import CountRow
from src.models.analytics.slice import CategoryRow, ProblemRow, RunRow, SourceRow
from src.models.enums import FetchStatus, SourceType

EPOCH_FLOOR = 1971


def known_time(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    moment = to_datetime(value)
    return moment if moment.year >= EPOCH_FLOOR else None


def to_counts(rows: Sequence[Sequence[Any]]) -> tuple[CountRow, ...]:
    return tuple(CountRow(str(row[0]), int(row[1])) for row in rows)


def to_category(row: Sequence[Any]) -> CategoryRow:
    return CategoryRow(
        code=str(row[0]),
        parent=str(row[1]),
        offers=int(row[2]),
        companies=int(row[3]),
        verified_sellers=int(row[4]),
        fresh=int(row[5]),
        priced=int(row[6]),
        searchable=int(row[7]),
        system_assigned=int(row[8]),
        source_reported=int(row[9]),
    )


def to_sources(
    sources: Sequence[Sequence[Any]],
    offers: Sequence[Sequence[Any]],
    attempts: Sequence[Sequence[Any]],
) -> tuple[SourceRow, ...]:
    counted = {to_uuid(row[0]): row for row in offers}
    journal = {to_uuid(row[0]): row for row in attempts}
    return tuple(
        _source(row, counted.get(to_uuid(row[0])), journal.get(to_uuid(row[0]))) for row in sources
    )


def _source(
    row: Sequence[Any], offers: Sequence[Any] | None, attempt: Sequence[Any] | None
) -> SourceRow:
    return SourceRow(
        source_id=to_uuid(row[0]),
        name=str(row[1]),
        provider_name=str(row[2]),
        source_type=SourceType(str(row[3])),
        offers=int(offers[1]) if offers else 0,
        companies=int(offers[2]) if offers else 0,
        fresh=int(offers[3]) if offers else 0,
        unknown_age=int(offers[4]) if offers else 0,
        last_seen_at=known_time(offers[5]) if offers else None,
        last_success_at=known_time(attempt[1]) if attempt else None,
        last_attempt_at=known_time(attempt[2]) if attempt else None,
        last_attempt_status=FetchStatus(str(attempt[3]))
        if attempt and known_time(attempt[2])
        else None,
        runs=int(attempt[4]) if attempt else 0,
        failed_runs=int(attempt[5]) if attempt else 0,
    )


def to_run(row: Sequence[Any]) -> RunRow:
    return RunRow(
        run_id=to_uuid(row[0]),
        source_id=to_uuid(row[1]),
        source_name=str(row[2]),
        provider_name=str(row[3]),
        started_at=to_datetime(row[4]),
        finished_at=to_datetime(row[5]),
        status=FetchStatus(str(row[6])),
        suppliers_extracted=int(row[7]),
        offers_extracted=int(row[8]),
        error_message=str(row[9]),
    )


def to_problem(row: Sequence[Any]) -> ProblemRow:
    return ProblemRow(
        source_id=to_uuid(row[0]),
        name=str(row[1]),
        offers=int(row[2]),
        no_supplier=int(row[3]),
        unverified_seller=int(row[4]),
        no_category=int(row[5]),
        no_price=int(row[6]),
        no_attributes=int(row[7]),
        stale=int(row[8]),
        unknown_age=int(row[9]),
    )
