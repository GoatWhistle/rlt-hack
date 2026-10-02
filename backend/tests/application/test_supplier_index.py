import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from types import SimpleNamespace, TracebackType
from typing import Any

import numpy as np
import pyarrow as arrow
import pytest
from pyarrow import parquet

from src.adapter.repository.errors import RepositoryUnavailableError
from src.adapter.repository.supplier_index.clickhouse import ClickHouseSupplierIndex
from src.application import supplier_index as module
from src.application.config import AppConfig
from src.models.search.supplier_search import SupplierCandidate
from src.service.errors import StorageUnavailableError

CARDS = [
    {"card_id": "c1", "supplier_inn": "1111111111", "category": "paper", "profile_text": "paper"},
    {"card_id": "c2", "supplier_inn": "2222222222", "category": "cable", "profile_text": "cable"},
]


def write_index(directory: Path) -> tuple[str, str]:
    parquet.write_table(arrow.Table.from_pylist(CARDS), directory / "cards.parquet")
    np.save(directory / "card_vectors.npy", np.array([[1, 0], [0, 1]], "float32"))
    (directory / "report.json").write_text("{}")
    files = {
        name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
        for name in ("cards.parquet", "card_vectors.npy", "report.json")
    }
    manifest = {
        "shape": [2, 2],
        "query_instruction": "test",
        "files": files,
        "history_before": "2025-01-01",
    }
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return files["card_vectors.npy"], files["cards.parquet"]


class FlakyGateway:
    def __init__(self, ready: list[tuple[Any, ...]]) -> None:
        self.ready = ready
        self.down = False
        self.archive: list[tuple[Any, ...]] = []
        self.archive_parameters: Mapping[str, Any] | None = None

    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        if self.down:
            raise RepositoryUnavailableError("connection refused")
        if "procurement_archive_imports" in statement:
            assert "status='completed'" in statement
            self.archive_parameters = parameters
            return self.archive
        return self.ready

    async def insert(
        self, table: str, column_names: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None:
        raise AssertionError("Supplier index only reads its gateway")


class FakeContainer:
    gateway_instance: FlakyGateway

    def __init__(self, config: object) -> None:
        self.config = config

    async def __aenter__(self) -> "FakeContainer":
        return self

    async def __aexit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def gateway(self) -> FlakyGateway:
        return self.gateway_instance


async def test_clickhouse_outage_becomes_storage_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index_id, cards_sha = write_index(tmp_path)
    gateway = FlakyGateway([(len(CARDS), 2, cards_sha)])
    FakeContainer.gateway_instance = gateway
    config = SimpleNamespace(clickhouse=SimpleNamespace(database="db"))
    monkeypatch.setattr(module, "Container", FakeContainer)
    monkeypatch.setattr(AppConfig, "from_env", staticmethod(lambda: config))
    monkeypatch.setenv("SUPPLIER_INDEX_DIR", str(tmp_path))
    monkeypatch.setenv("SUPPLIER_INDEX_ID", index_id)
    monkeypatch.delenv("SUPPLIER_RANKER_DIR", raising=False)
    async with module.supplier_index() as index:
        gateway.down = True
        with pytest.raises(StorageUnavailableError):
            await index.enrich([SupplierCandidate("1111111111", "paper", "", 1.0, 1.0)])
        with pytest.raises(StorageUnavailableError):
            await index.search("paper", [1.0, 0.0], 1)


async def test_completed_archive_changes_index_cache_version_after_restart(tmp_path: Path) -> None:
    index_id, cards_sha = write_index(tmp_path)
    gateway = FlakyGateway([(len(CARDS), 2, cards_sha)])
    pending = ClickHouseSupplierIndex(tmp_path, gateway, index_id, "db")
    await pending.initialize()
    assert pending.version.endswith("/full-history-v1/pending")
    assert gateway.archive_parameters == {"index": index_id, "before": date(2025, 1, 1)}
    gateway.archive = [("b" * 64,)]
    completed = ClickHouseSupplierIndex(tmp_path, gateway, index_id, "db")
    await completed.initialize()
    assert completed.version.endswith("/full-history-v1/completed/" + "b" * 64)
    assert completed.version != pending.version


async def test_invalid_completed_archive_does_not_claim_ready(tmp_path: Path) -> None:
    index_id, cards_sha = write_index(tmp_path)
    gateway = FlakyGateway([(len(CARDS), 2, cards_sha)])
    gateway.archive = [("invalid-checksum",)]
    index = ClickHouseSupplierIndex(tmp_path, gateway, index_id, "db")
    with pytest.raises(ValueError, match="archive identity"):
        await index.initialize()
