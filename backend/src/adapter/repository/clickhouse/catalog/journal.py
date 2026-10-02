"""Репозиторий журнала обхода: завершённые обходы источников.

Название таблицы схемы сохранено: `crawl_runs`.
"""

from uuid import UUID

from src.adapter.repository.clickhouse.engine.rows import to_datetime, to_uuid
from src.adapter.repository.clickhouse.engine.versions import event_version
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.models.enums import FetchStatus
from src.models.operations.journal import CrawlRun

RUN_COLUMNS = (
    "run_id",
    "source_id",
    "started_at",
    "finished_at",
    "status",
    "suppliers_extracted",
    "offers_extracted",
    "provider_name",
    "error_message",
    "version",
)

_SELECT = (
    "SELECT run_id, source_id, started_at, finished_at, status, suppliers_extracted, "
    "offers_extracted, provider_name, error_message FROM {db}.crawl_runs"
)


class ClickHouseJournalRepository:
    """Версия записи журнала выводится из её времени: повтор не создаёт новую."""

    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._db = database

    async def save_run(self, run: CrawlRun) -> None:
        await self._gateway.insert(
            f"{self._db}.crawl_runs",
            RUN_COLUMNS,
            [
                (
                    run.run_id,
                    run.source_id,
                    run.started_at,
                    run.finished_at,
                    str(run.status),
                    run.suppliers_extracted,
                    run.offers_extracted,
                    run.provider_name,
                    run.error_message,
                    event_version(run.started_at),
                )
            ],
        )

    async def last_runs(self, source_id: UUID, limit: int = 10) -> list[CrawlRun]:
        """Последние обходы источника: нужны оператору джобы."""
        rows = await self._gateway.select(
            _SELECT.format(db=self._db) + " WHERE source_id = {source_id:UUID} "
            "ORDER BY started_at DESC LIMIT {limit:UInt32}",
            {"source_id": str(source_id), "limit": limit},
        )
        return [
            CrawlRun(
                run_id=to_uuid(row[0]),
                source_id=to_uuid(row[1]),
                started_at=to_datetime(row[2]),
                finished_at=to_datetime(row[3]),
                status=FetchStatus(str(row[4])),
                suppliers_extracted=int(row[5]),
                offers_extracted=int(row[6]),
                provider_name=str(row[7]),
                error_message=str(row[8]),
            )
            for row in rows
        ]
