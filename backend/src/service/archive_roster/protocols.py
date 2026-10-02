from typing import Protocol

from src.models.archive_roster import RosterSnapshot


class RosterSource(Protocol):
    @property
    def name(self) -> str: ...

    async def read(self) -> RosterSnapshot: ...


class RosterStore(Protocol):
    async def saved(self, version: str) -> int | None: ...

    async def save(self, snapshot: RosterSnapshot, source_name: str) -> None: ...
