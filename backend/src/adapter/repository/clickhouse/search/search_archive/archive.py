from collections.abc import Sequence
from uuid import UUID

from src.adapter.repository.clickhouse.engine.rows import to_datetime, to_uuid
from src.adapter.repository.clickhouse.engine.versions import event_version
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.search.search_archive.result_dto import (
    decode_result,
    encode_result,
)
from src.models.enums import Locale
from src.models.search.search import SearchText
from src.models.search.search_result import SearchHistory, SearchResult, SearchSummary

SEARCH_COLUMNS = (
    "search_id",
    "text",
    "locale",
    "payload",
    "candidates",
    "recommended",
    "items",
    "created_at",
    "version",
    "is_deleted",
)
SELECT_PAYLOAD = (
    "SELECT payload FROM {db}.searches_current WHERE search_id = {{search_id:UUID}} LIMIT 1"
)
SELECT_RECENT = (
    "SELECT search_id, text, locale, items, candidates, recommended, created_at "
    "FROM {db}.searches_current {where}"
    "ORDER BY created_at DESC, search_id DESC LIMIT {{limit:UInt32}}"
)
AFTER_CURSOR = (
    "WHERE (created_at, search_id) < ("
    "SELECT created_at, search_id FROM {db}.searches_current "
    "WHERE search_id = {{before:UUID}} LIMIT 1) "
)
COUNT_SEARCHES = "SELECT count() FROM {db}.searches_current"


class ClickHouseSearchArchive:
    def __init__(
        self,
        gateway: SqlGateway,
        database: str = "supplier_search",
        writer: SqlGateway | None = None,
    ) -> None:
        self._gateway = gateway
        self._writer = writer or gateway
        self._db = database

    async def save(self, result: SearchResult) -> None:
        summary = result.summary()
        await self._writer.insert(
            f"{self._db}.searches",
            SEARCH_COLUMNS,
            [
                (
                    result.search_id,
                    summary.text.value,
                    str(summary.locale),
                    encode_result(result),
                    summary.candidates,
                    summary.recommended,
                    summary.items,
                    result.created_at,
                    event_version(result.created_at),
                    0,
                )
            ],
        )

    async def get(self, search_id: UUID) -> SearchResult | None:
        rows = await self._gateway.select(
            SELECT_PAYLOAD.format(db=self._db), {"search_id": str(search_id)}
        )
        return decode_result(str(rows[0][0])) if rows else None

    async def recent(self, limit: int, before: UUID | None = None) -> SearchHistory:
        if limit < 1:
            return SearchHistory(searches=(), has_more=False, total=0)
        where = AFTER_CURSOR.format(db=self._db) if before is not None else ""
        parameters: dict[str, object] = {"limit": limit + 1}
        if before is not None:
            parameters["before"] = str(before)
        rows = await self._gateway.select(
            SELECT_RECENT.format(db=self._db, where=where), parameters
        )
        counted = await self._gateway.select(COUNT_SEARCHES.format(db=self._db), {})
        return SearchHistory(
            searches=tuple(_summary(row) for row in rows[:limit]),
            has_more=len(rows) > limit,
            total=int(str(counted[0][0])) if counted else 0,
        )


def _summary(row: Sequence[object]) -> SearchSummary:
    return SearchSummary(
        search_id=to_uuid(row[0]),
        text=SearchText(str(row[1])),
        locale=Locale(str(row[2])),
        items=int(str(row[3])),
        candidates=int(str(row[4])),
        recommended=int(str(row[5])),
        created_at=to_datetime(row[6]),
    )
