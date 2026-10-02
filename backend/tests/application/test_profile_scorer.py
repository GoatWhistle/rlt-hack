from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from src.adapter.repository.supplier_index.clickhouse import ClickHouseSupplierIndex
from src.models.search.search_context import SearchContext
from src.models.search.supplier_search import SupplierCandidate


class Gateway:
    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        raise AssertionError("Configured scorer must not scan ClickHouse embeddings")

    async def insert(
        self, table: str, column_names: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None:
        raise AssertionError("Profile scoring must not modify data")


class Scorer:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.failure = False

    async def score(self, index_id: str, vector: list[float], card_count: int) -> list[float]:
        assert index_id == "index"
        assert card_count == 2
        if self.failure:
            raise RuntimeError("GPU scorer unavailable")
        return self.scores


async def no_candidates(candidates: list[SupplierCandidate]) -> list[SupplierCandidate]:
    return []


async def test_gpu_scoring_preserves_model_fusion_and_skips_clickhouse_scan(tmp_path: Path) -> None:
    scorer = Scorer([0.2, 0.8])
    index = cast(Any, ClickHouseSupplierIndex(tmp_path, Gateway(), "index", "db", scorer))
    index.cards = [{}, {}]
    index.manifest = {"files": {"card_vectors.npy": "index"}, "history_before": "2025-01-01"}
    observed: list[np.ndarray[Any, Any]] = []

    def fuse(
        text: str, dense: np.ndarray[Any, Any], limit: int, context: SearchContext
    ) -> list[SupplierCandidate]:
        observed.append(dense)
        return []

    index._fuse = fuse
    index.enrich = no_candidates
    assert index.version.endswith("/gpu-profile-scores-v1")
    assert await index.search_context("paper", [1.0, 0.0], 10, SearchContext()) == []
    assert len(observed) == 1
    assert observed[0].dtype == np.float32
    np.testing.assert_allclose(observed[0], [0.2, 0.8])
    scorer.failure = True
    with pytest.raises(RuntimeError, match="GPU scorer unavailable"):
        await index.search_context("paper", [1.0, 0.0], 10, SearchContext())


@pytest.mark.parametrize("scores", [[0.2], [float("nan"), 0.2]])
async def test_invalid_scores_do_not_reach_model(tmp_path: Path, scores: list[float]) -> None:
    index = cast(Any, ClickHouseSupplierIndex(tmp_path, Gateway(), "index", "db", Scorer(scores)))
    index.cards = [{}, {}]
    with pytest.raises(ValueError, match="similarity scores"):
        await index.search_context("paper", [1.0, 0.0], 10, SearchContext())
