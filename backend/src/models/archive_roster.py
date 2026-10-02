from collections.abc import Collection
from dataclasses import dataclass

from src.models.enums import Novelty
from src.models.errors import InvalidArchiveRosterError
from src.models.inn import is_valid_inn


@dataclass(frozen=True, slots=True)
class ArchiveRoster:
    version: str
    known: frozenset[str]

    def __post_init__(self) -> None:
        if not self.version:
            raise InvalidArchiveRosterError("roster version is empty")

    def novelty_of(self, inn: str | None) -> Novelty:
        if inn is None or not is_valid_inn(inn):
            return Novelty.UNKNOWN
        return Novelty.KNOWN if inn in self.known else Novelty.NEW


@dataclass(frozen=True, slots=True)
class RosterSnapshot:
    version: str
    inns: frozenset[str]

    @classmethod
    def of(cls, version: str, inns: Collection[str]) -> "RosterSnapshot":
        valid = frozenset(inn for inn in inns if is_valid_inn(inn))
        if not valid:
            raise InvalidArchiveRosterError("roster has no valid inn")
        return cls(version, valid)
