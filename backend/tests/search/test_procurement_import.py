import asyncio
import json
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import pytest

from src.adapter.repository.procurement_import.columns import COLUMNS
from src.adapter.repository.procurement_import.importer import import_procurements


class Gateway:
    def __init__(self) -> None:
        self.registry: list[tuple[Any, ...]] = []
        self.tables: dict[str, dict[Any, tuple[Any, ...]]] = {name: {} for name in COLUMNS}
        self.batch_lengths: list[int] = []
        self.fail_once = False

    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        if "procurement_archive_imports" in statement:
            return self.registry
        table = statement.split(" FROM ")[1].split(".")[1].removesuffix("_current")
        return [(len(self.tables[table]),)]

    async def insert(
        self, table: str, columns: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None:
        name = table.split(".")[1]
        if name == "procurement_archive_imports":
            self.registry = [tuple(rows[0])]
            return
        self.batch_lengths.append(len(rows))
        for row in rows:
            key = tuple(row[:3]) if name == "lot_participations" else row[0]
            self.tables[name][key] = tuple(row)
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("interrupted transfer")


def prepare(path: Path) -> None:
    with duckdb.connect(str(path)) as connection:
        connection.execute("""
            CREATE TABLE lot_info AS SELECT * FROM (VALUES
              ('old', 'p1', 'paper', 'paper subject', 100.25, true, '0000000001',
               'EM', DATE '2024-01-01', false, 1),
              ('missing', NULL, 'pump', '', NULL, NULL, NULL,
               'AIS', DATE '2024-02-01', false, 1),
              ('boundary', 'p3', 'future', '', 1, false, NULL,
               'EM', DATE '2025-01-01', false, 1),
              ('conflicted', 'p4', 'bad', '', 1, false, NULL,
               'EM', DATE '2024-03-01', true, 1)
            ) t(lot_id, procedure_id, procedure_name, subject, start_price, is_smp,
                customer_inn, source_system, publish_date, notice_conflict, winner_count);
            CREATE TABLE products AS SELECT * FROM (VALUES
                ('old', 'Paper A4', '17.12.14.110'), ('old', 'Paper A3', NULL),
                ('missing', 'Pump', '28.13.11'), ('boundary', 'Future', '99.99'),
                ('conflicted', 'Bad', '99.99'), ('orphan', 'Orphan', '99.99')
            ) t(lot_id, product_name, okpd2_code);
            CREATE TABLE participations AS SELECT * FROM (VALUES
                ('old', '0000000001', true, false),
                ('missing', '0000000002', true, true),
                ('boundary', '0000000003', true, false)
            ) t(lot_id, supplier_inn, is_winner, label_conflict);
        """)


async def inputs(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "prepared.duckdb"
    await asyncio.to_thread(prepare, source)
    directory = tmp_path / "index"
    directory.mkdir()
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "history_before": "2025-01-01",
                "files": {"card_vectors.npy": "a" * 64},
            }
        )
    )
    return source, directory


@pytest.mark.asyncio
async def test_full_archive_cutoff_missing_data_and_repeat(tmp_path: Path) -> None:
    source, directory = await inputs(tmp_path)
    gateway = Gateway()
    report = await import_procurements(gateway, "supplier_search", source, directory, 1)
    assert report["counts"] == {
        "procurement_lots": 2,
        "procurement_items": 3,
        "lot_participations": 2,
    }
    assert max(gateway.batch_lengths) == 1
    lots = gateway.tables["procurement_lots"]
    assert set(lots) == {"old", "missing"}
    assert lots["old"][6] == 1
    assert lots["old"][12] == date(2024, 1, 1)
    assert lots["missing"][5:9] == (None, None, None, None)
    assert lots["missing"][1:3] == ("", "")
    participants = gateway.tables["lot_participations"]
    assert participants[("old", "0000000001", "")][4] == 1
    assert participants[("missing", "0000000002", "")][4] == 0
    assert participants[("missing", "0000000002", "")][-1] == "unconfirmed"
    copied = {name: dict(rows) for name, rows in gateway.tables.items()}
    repeated = await import_procurements(gateway, "supplier_search", source, directory, 1)
    assert repeated["already_present"]
    assert copied == gateway.tables
    assert gateway.registry[0][-1] == "completed"


@pytest.mark.asyncio
async def test_partial_import_can_resume_without_duplicate_keys(tmp_path: Path) -> None:
    source, directory = await inputs(tmp_path)
    gateway = Gateway()
    gateway.fail_once = True
    with pytest.raises(RuntimeError, match="interrupted"):
        await import_procurements(gateway, "supplier_search", source, directory, 1)
    assert gateway.registry[0][-1] == "importing"
    result = await import_procurements(gateway, "supplier_search", source, directory, 1)
    assert result["counts"]["procurement_lots"] == 2
    assert gateway.registry[0][-1] == "completed"


@pytest.mark.asyncio
async def test_foreign_snapshot_or_missing_audit_are_rejected(tmp_path: Path) -> None:
    source, directory = await inputs(tmp_path)
    gateway = Gateway()
    gateway.tables["procurement_lots"]["foreign"] = ("foreign",)
    with pytest.raises(ValueError, match="no import audit"):
        await import_procurements(gateway, "supplier_search", source, directory)
    gateway.tables["procurement_lots"].clear()
    await import_procurements(gateway, "supplier_search", source, directory)
    gateway.tables["procurement_items"].clear()
    with pytest.raises(ValueError, match="differ from audit"):
        await import_procurements(gateway, "supplier_search", source, directory)
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "history_before": "2026-01-01",
                "files": {"card_vectors.npy": "b" * 64},
            }
        )
    )
    with pytest.raises(ValueError, match="another snapshot"):
        await import_procurements(gateway, "supplier_search", source, directory)
