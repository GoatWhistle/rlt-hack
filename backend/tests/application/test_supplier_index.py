import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace, TracebackType
from typing import Any

import numpy as np
import pyarrow as arrow
import pytest
from pyarrow import parquet

from src.adapter.repository.errors import RepositoryUnavailableError
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
    manifest = {"shape": [2, 2], "query_instruction": "test", "files": files}
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return files["card_vectors.npy"], files["cards.parquet"]


class FlakyGateway:
    def __init__(self, ready: list[tuple[Any, ...]]) -> None:
        self.ready = ready
        self.down = False

    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        if self.down:
            raise RepositoryUnavailableError("connection refused")
        return self.ready


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
