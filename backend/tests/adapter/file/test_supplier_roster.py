from pathlib import Path

import pytest

from src.adapter.file.errors import MissingInnColumnError
from src.adapter.file.supplier_roster.reader import CsvSupplierRoster, read_roster


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


async def test_roster_normalizes_inns_and_versions_by_content(tmp_path: Path) -> None:
    first = write(
        tmp_path / "a.csv",
        "lot_id,supplier_inn,is_winner\n1,7801234564,1\n2,7707083893,0\n3,7801234564,0\n4,,0\n",
    )
    second = write(tmp_path / "b.csv", "supplier_inn,lot_id\n7707083893,9\n7801234564,8\n")
    roster = await CsvSupplierRoster(first).read()
    assert roster.inns == frozenset({"7801234564", "7707083893"})
    assert roster.version == read_roster(second).version
    assert roster.version.startswith("inn-")
    assert CsvSupplierRoster(first).name == "a.csv"


def test_roster_needs_the_inn_column(tmp_path: Path) -> None:
    with pytest.raises(MissingInnColumnError):
        read_roster(write(tmp_path / "c.csv", "lot_id\n1\n"))
