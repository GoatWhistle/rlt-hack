from dataclasses import dataclass, field

from src.models.archive_roster import RosterSnapshot
from src.service.archive_roster.importer import ArchiveRosterImporter

SNAPSHOT = RosterSnapshot.of("inn-1", ["7801234564", "7707083893"])


@dataclass
class FakeSource:
    name: str = "suppliers.csv"

    async def read(self) -> RosterSnapshot:
        return SNAPSHOT


@dataclass
class FakeStore:
    rows: dict[str, int] = field(default_factory=dict)
    saves: int = 0

    async def saved(self, version: str) -> int | None:
        return self.rows.get(version)

    async def save(self, snapshot: RosterSnapshot, source_name: str) -> None:
        self.saves += 1
        self.rows[snapshot.version] = len(snapshot.inns)


async def test_roster_is_loaded_once_and_then_recognised() -> None:
    store = FakeStore()
    first = await ArchiveRosterImporter(FakeSource(), store).run()
    assert (first.version, first.suppliers, first.already_present) == ("inn-1", 2, False)
    again = await ArchiveRosterImporter(FakeSource(), store).run()
    assert again.already_present
    assert store.saves == 1


async def test_incomplete_set_is_written_again() -> None:
    store = FakeStore(rows={"inn-1": 1})
    assert not (await ArchiveRosterImporter(FakeSource(), store).run()).already_present
    assert store.rows["inn-1"] == 2
