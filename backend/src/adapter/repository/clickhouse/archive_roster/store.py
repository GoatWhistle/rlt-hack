from collections.abc import Sequence

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.models.archive_roster import ArchiveRoster, RosterSnapshot

ROSTER_BATCH = 50_000
SELECT_ACTIVE = (
    "SELECT argMax(set_version, imported_at), count() FROM {db}.archive_supplier_sets FINAL"
)
SELECT_KNOWN = (
    "SELECT inn FROM {db}.archive_suppliers FINAL "
    "WHERE set_version = {{version:String}} AND inn IN {{inns:Array(String)}}"
)
SELECT_SET = (
    "SELECT row_count FROM {db}.archive_supplier_sets FINAL WHERE set_version = {{version:String}}"
)


class ClickHouseArchiveRoster:
    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._db = database

    async def roster(self, inns: Sequence[str]) -> ArchiveRoster | None:
        rows = await self._gateway.select(SELECT_ACTIVE.format(db=self._db))
        if not rows or not int(str(rows[0][1])):
            return None
        version = str(rows[0][0])
        wanted = sorted({inn for inn in inns if inn})
        if not wanted:
            return ArchiveRoster(version, frozenset())
        found = await self._gateway.select(
            SELECT_KNOWN.format(db=self._db), {"version": version, "inns": wanted}
        )
        return ArchiveRoster(version, frozenset(str(row[0]) for row in found))

    async def saved(self, version: str) -> int | None:
        rows = await self._gateway.select(SELECT_SET.format(db=self._db), {"version": version})
        return int(str(rows[0][0])) if rows else None

    async def save(self, snapshot: RosterSnapshot, source_name: str) -> None:
        ordered = sorted(snapshot.inns)
        for start in range(0, len(ordered), ROSTER_BATCH):
            await self._gateway.insert(
                f"{self._db}.archive_suppliers",
                ("set_version", "inn"),
                [(snapshot.version, inn) for inn in ordered[start : start + ROSTER_BATCH]],
            )
        await self._gateway.insert(
            f"{self._db}.archive_supplier_sets",
            ("set_version", "row_count", "source_name"),
            [(snapshot.version, len(ordered), source_name)],
        )
