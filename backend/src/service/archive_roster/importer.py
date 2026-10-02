from dataclasses import dataclass

from src.service.archive_roster.protocols import RosterSource, RosterStore


@dataclass(frozen=True, slots=True)
class RosterImport:
    version: str
    suppliers: int
    already_present: bool


class ArchiveRosterImporter:
    def __init__(self, source: RosterSource, store: RosterStore) -> None:
        self._source = source
        self._store = store

    async def run(self) -> RosterImport:
        snapshot = await self._source.read()
        saved = await self._store.saved(snapshot.version)
        if saved == len(snapshot.inns):
            return RosterImport(snapshot.version, saved, already_present=True)
        await self._store.save(snapshot, self._source.name)
        return RosterImport(snapshot.version, len(snapshot.inns), already_present=False)
