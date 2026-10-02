import asyncio
import csv
import hashlib
from pathlib import Path

from src.adapter.file.errors import MissingInnColumnError
from src.models.archive_roster import RosterSnapshot
from src.models.inn import normalize_inn

INN_COLUMN = "supplier_inn"
VERSION_LENGTH = 16


def read_roster(path: Path) -> RosterSnapshot:
    inns: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if INN_COLUMN not in (reader.fieldnames or ()):
            raise MissingInnColumnError(path.name, INN_COLUMN)
        for row in reader:
            inn = normalize_inn(row.get(INN_COLUMN))
            if inn is not None:
                inns.add(inn)
    digest = hashlib.sha256("\n".join(sorted(inns)).encode("ascii")).hexdigest()
    return RosterSnapshot.of(f"inn-{digest[:VERSION_LENGTH]}", inns)


class CsvSupplierRoster:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def name(self) -> str:
        return self._path.name

    async def read(self) -> RosterSnapshot:
        return await asyncio.to_thread(read_roster, self._path)
