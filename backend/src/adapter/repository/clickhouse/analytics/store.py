import logging

from pydantic import TypeAdapter, ValidationError

from src.adapter.repository.clickhouse.engine.rows import to_datetime
from src.adapter.repository.clickhouse.engine.versions import event_version
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.models.analytics.filters import DEFINITIONS_VERSION
from src.models.analytics.slice import AnalyticsSlice

logger = logging.getLogger(__name__)

SNAPSHOT_COLUMNS = (
    "snapshot_id",
    "scope_key",
    "definitions_version",
    "as_of",
    "computed_at",
    "payload",
    "version",
)
SELECT_LATEST = (
    "SELECT payload FROM {db}.analytics_snapshots_current "
    "WHERE scope_key = {{scope_key:String}} AND definitions_version = {{definitions:String}} "
    "ORDER BY as_of DESC, computed_at DESC LIMIT 1"
)
CODEC: TypeAdapter[AnalyticsSlice] = TypeAdapter(AnalyticsSlice)


class ClickHouseSliceStore:
    def __init__(
        self,
        gateway: SqlGateway,
        database: str = "supplier_search",
        writer: SqlGateway | None = None,
    ) -> None:
        self._gateway = gateway
        self._writer = writer or gateway
        self._db = database

    async def latest(self, scope_key: str) -> AnalyticsSlice | None:
        rows = await self._gateway.select(
            SELECT_LATEST.format(db=self._db),
            {"scope_key": scope_key, "definitions": DEFINITIONS_VERSION},
        )
        if not rows:
            return None
        try:
            return CODEC.validate_json(str(rows[0][0]))
        except ValidationError:
            logger.warning("Срез аналитики %s не читается и пропущен", scope_key)
            return None

    async def publish(self, snapshot: AnalyticsSlice) -> None:
        await self._writer.insert(
            f"{self._db}.analytics_snapshots",
            SNAPSHOT_COLUMNS,
            [
                (
                    snapshot.snapshot_id,
                    snapshot.filters.scope_key,
                    snapshot.definitions_version,
                    to_datetime(snapshot.as_of),
                    to_datetime(snapshot.computed_at),
                    CODEC.dump_json(snapshot).decode(),
                    event_version(snapshot.computed_at),
                )
            ],
        )
