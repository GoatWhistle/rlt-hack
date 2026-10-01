from pathlib import Path

import numpy as np
import pytest

from rlt_ml.common import read_config
from rlt_ml.ranker import ranking_metrics, train
from rlt_ml.retrieval import evaluate, reciprocal_rank_fusion, summarize, unique_suppliers


def test_rank_metrics_include_misses_and_ties():
    result = ranking_metrics(["a", "a", "b", "b"], [0, 1, 1, 0], [2, 1, 2, 1])
    assert result["hit_at_1"] == 0.5
    assert result["mrr"] == 0.75
    with pytest.raises(ValueError):
        ranking_metrics(["a", "a"], [1, 1], [1, 2])


def test_supplier_aggregation_does_not_reward_card_count():
    result = unique_suppliers(np.array([0.9, 0.8, 0.7, 0.85]), ["a", "a", "a", "b"], 2)
    assert result == ["a", "b"]
    assert unique_suppliers(np.zeros(4), ["a", "a", "a", "b"], 2, positive_only=True) == []


def test_recall_keeps_unseen_supplier_in_denominator():
    result = summarize([{"participants": ["seen", "new"], "candidate_inns": ["seen"],
                         "winner_inn": "new"}])
    assert result["recall_at_100"] == 0.5
    assert result["winner_recall_at_100"] == 0


def test_hybrid_uses_both_rankings_and_deduplicates():
    assert reciprocal_rank_fusion(["a", "b"], ["b", "c"])[0] == "b"
    assert len(reciprocal_rank_fusion(["a", "b"], ["b", "c"])) == 3


def test_ranker_and_retrieval_commands_work(prepared, tmp_path):
    data, _ = prepared
    report = train(data, tmp_path / "ranker", iterations=3, max_lots=4)
    assert report["validation"]["catboost"]["lots"] == 4
    assert "test" not in report
    config = read_config(Path(__file__).resolve().parents[1] / "configs/retrieval.toml")
    report = evaluate(data, tmp_path / "retrieval", "validation", "tfidf", config)
    assert report["all"]["queries"] == 8
    assert report["with_unseen_supplier"]["queries"] >= 1
