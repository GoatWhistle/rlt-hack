from collections.abc import Sequence
from uuid import UUID

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.rows import to_datetime, to_uuid
from src.adapter.repository.clickhouse.search_archive.result_dto import (
    decode_result,
    encode_result,
)
from src.adapter.repository.clickhouse.versions import event_version
from src.models.enums import Locale
from src.models.search import SearchText
from src.models.search_result import SearchResult, SearchSummary

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
    "FROM {db}.searches_current ORDER BY created_at DESC, search_id LIMIT {{limit:UInt32}}"
)


class ClickHouseSearchArchive:
    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._db = database

    async def save(self, result: SearchResult) -> None:
        summary = result.summary()
        await self._gateway.insert(
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

    async def recent(self, limit: int) -> tuple[SearchSummary, ...]:
        if limit < 1:
            return ()
        rows = await self._gateway.select(SELECT_RECENT.format(db=self._db), {"limit": limit})
        return tuple(_summary(row) for row in rows)


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
