import json
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from chdb import session

from src.adapter.repository.supplier_index.archive_history import _query, enrich_archive_history
from src.models.search.search_context import SearchContext
from src.models.search.supplier_search import SupplierCandidate, SupplierPurchase


class Gateway:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready
        self.parameters: list[Mapping[str, Any]] = []
        self.error = False

    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        assert parameters is not None
        self.parameters.append(parameters)
        if self.error:
            raise RuntimeError("database unavailable")
        if "procurement_archive_imports" in statement:
            return [(int(self.ready),)]
        assert "archive_index_id={index:String}" in statement
        assert "publish_date < {before:Date}" in statement
        assert "supplier_inn IN {inns:Array(String)}" in statement
        assert "LIMIT 5 BY supplier_inn" in statement
        assert "max_memory_usage=536870912" in statement
        return [
            (inn, "old-real-lot", "Paper A4", date(2024, 1, 1), "", "EM", ["Paper A4"], 1)
            for inn in parameters["inns"]
        ]

    async def insert(
        self, table: str, column_names: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None:
        raise AssertionError("Archive enrichment must not insert offers or history")


@pytest.mark.asyncio
async def test_completed_archive_batches_and_preserves_full_counts() -> None:
    gateway = Gateway()
    candidates = [
        SupplierCandidate(
            str(number), "17.12", "profile", 0.5, 0.5, category_lots=100, category_wins=20
        )
        for number in range(23)
    ]
    context = SearchContext(okpd2_codes=("17.12.14.110",))
    result = await enrich_archive_history(
        gateway,
        "supplier_search",
        "index",
        date(2025, 1, 1),
        "Paper A4",
        context,
        candidates,
    )
    assert len(gateway.parameters) == 4
    assert [len(params["inns"]) for params in gateway.parameters[1:]] == [10, 10, 3]
    assert gateway.parameters[1]["codes"] == ["17.12.14.110"]
    assert gateway.parameters[1]["categories"] == ["17.12"]
    assert result[0].purchases[0].publish_date == "2024-01-01"
    assert result[0].purchases[0].product_names == ["Paper A4"]
    assert result[0].category_lots == 100
    assert result[0].category_wins == 20
    assert result[0].score == 0.5
    assert candidates[0].purchases == []


@pytest.mark.asyncio
async def test_unfinished_import_retains_existing_samples() -> None:
    sample = SupplierPurchase("sample", "Paper", "2024-01-01", "", "EM", [], False)
    candidate = SupplierCandidate("inn", "17.12", "", 0.5, 0.5, purchases=[sample])
    gateway = Gateway(False)
    result = await enrich_archive_history(
        gateway,
        "supplier_search",
        "index",
        date(2025, 1, 1),
        "Paper",
        SearchContext(),
        [candidate],
    )
    assert result == [candidate]
    assert len(gateway.parameters) == 1


@pytest.mark.asyncio
async def test_channel_error_is_not_silently_replaced_with_samples() -> None:
    gateway = Gateway()
    gateway.error = True
    with pytest.raises(RuntimeError, match="database unavailable"):
        await enrich_archive_history(
            gateway,
            "supplier_search",
            "index",
            date(2025, 1, 1),
            "Paper",
            SearchContext(),
            [SupplierCandidate("inn", "17.12", "", 0.5, 0.5)],
        )


@pytest.mark.chdb
def test_real_query_selects_relevant_full_history_and_excludes_future(tmp_path: Path) -> None:
    database = session.Session(str(tmp_path / "chdb"))
    try:
        database.query("CREATE DATABASE archive_test")
        database.query(
            "CREATE TABLE archive_test.procurement_lots_current (lot_id String, "
            "procedure_name String, subject String, publish_date Date, "
            "customer_inn Nullable(String), platform String, archive_index_id String, "
            "archive_history_before Date) ENGINE=MergeTree ORDER BY lot_id"
        )
        database.query(
            "CREATE TABLE archive_test.lot_participations_current (lot_id String, "
            "supplier_inn String, is_winner UInt8, winner_label_status String) "
            "ENGINE=MergeTree ORDER BY lot_id"
        )
        database.query(
            "CREATE TABLE archive_test.procurement_items_current (lot_id String, "
            "product_name String, okpd2_code String) ENGINE=MergeTree ORDER BY lot_id"
        )
        for lot, title, published, index in (
            ("old", "Paper A4", "2024-01-01", "snapshot"),
            ("new", "Shoes", "2024-12-01", "snapshot"),
            ("future", "Paper A4", "2025-01-01", "snapshot"),
            ("foreign", "Paper A4", "2024-01-01", "other-index"),
        ):
            database.query(
                "INSERT INTO archive_test.procurement_lots_current VALUES "
                f"('{lot}', '{title}', '', '{published}', NULL, 'EM', '{index}', '2025-01-01')"
            )
            database.query(
                "INSERT INTO archive_test.lot_participations_current VALUES "
                f"('{lot}', 'inn', 1, 'confirmed')"
            )
            code = "15.20.1" if lot == "new" else "17.12.14.110"
            database.query(
                "INSERT INTO archive_test.procurement_items_current VALUES "
                f"('{lot}', '{title}', '{code}')"
            )
        query = _query("archive_test")
        for key, value in {
            "{index:String}": "'snapshot'",
            "{before:Date}": "toDate('2025-01-01')",
            "{inns:Array(String)}": "['inn']",
            "{codes:Array(String)}": "['17.12.14.110']",
            "{categories:Array(String)}": "['17.12']",
            "{terms:Array(String)}": "['paper', 'a4']",
        }.items():
            query = query.replace(key, value)
        rows = json.loads(str(database.query(query, "JSON")))["data"]
        assert [row["lot_id"] for row in rows] == ["old"]
        assert rows[0]["names"] == ["Paper A4"]
    finally:
        database.close()
