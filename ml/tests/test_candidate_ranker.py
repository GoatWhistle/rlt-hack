import json

import pytest

from rlt_ml.candidate_ranker import _load_predictions, _rank_metrics


def test_rank_metrics_counts_retrieval_misses_as_zero():
    rows = [
        {"lot_id": "1", "winner_inn": "a"},
        {"lot_id": "2", "winner_inn": "b"},
        {"lot_id": "3", "winner_inn": None},
    ]
    metrics = _rank_metrics(rows, {"1": ["a", "x"], "2": ["x", "b"], "3": ["z"]})

    assert metrics["lots_with_unique_winner"] == 2
    assert metrics["winner_recall_in_candidates"] == 1
    assert metrics["hit_at_1"] == 0.5
    assert metrics["hit_at_5"] == 1
    assert metrics["mrr"] == 0.75


def test_rank_metrics_counts_absent_winner_as_miss():
    rows = [{"lot_id": "1", "winner_inn": "a"}]

    metrics = _rank_metrics(rows, {"1": ["x", "y"]})

    assert metrics["winner_recall_in_candidates"] == 0
    assert metrics["hit_at_1"] == 0
    assert metrics["hit_at_5"] == 0
    assert metrics["mrr"] == 0


def test_predictions_require_nonempty_candidates_and_unique_lots(tmp_path):
    source = tmp_path / "predictions.jsonl"
    source.write_text(json.dumps({"lot_id": "1", "candidate_inns": []}) + "\n")

    with pytest.raises(ValueError, match="Нет retrieval-кандидатов"):
        _load_predictions(source)
