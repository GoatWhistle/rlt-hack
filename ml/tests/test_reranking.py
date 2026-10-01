import importlib.util
import json
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from rlt_ml.reranking.candidates import build
from rlt_ml.reranking.features import FEATURES, feature_row
from rlt_ml.reranking.train import metrics, train


def test_features_use_only_observable_inputs():
    query = {"query_text": "Поставка бумаги", "start_price": None}
    card = {
        "profile_text": "Поставка бумаги офисной",
        "example_count": 3,
        "profile_last_date": date(2024, 1, 1),
    }
    values = feature_row(
        query,
        card,
        {"participations": 4, "wins": 2},
        {},
        {},
        [0.8, 3, 0.02, 1, 2, 301],
        date(2024, 6, 1),
        2,
    )
    result = dict(zip(FEATURES, values, strict=True))
    assert result["token_coverage"] == 1
    assert result["supplier_win_rate"] == 0.5
    assert result["missing_customer"] == result["missing_price"] == 1
    assert np.isnan(result["price_distance"])
    assert result["profile_age"] > 0


def test_metrics_keep_unretrieved_winners():
    rows = [
        {"lot_id": "a", "participants": ["x"], "winner_inn": "x"},
        {"lot_id": "b", "participants": ["z"], "winner_inn": "z"},
    ]
    report = metrics(rows, {"a": ["x"], "b": ["y"]})
    assert report["winner_mrr"] == report["winner_hit_1"] == 0.5
    assert report["winner_recall_200"] == report["participant_recall_10"] == 0.5


def test_candidate_training_with_synthetic_temporal_data(prepared, tmp_path):
    data, _ = prepared
    folders = []
    for split in ("train", "validation"):
        vectors = tmp_path / (split + "-vectors")
        vectors.mkdir()
        cards = pq.read_table(data / split / "cards.parquet")
        queries = pq.read_table(data / split / "queries.parquet")
        pq.write_table(cards, vectors / "cards.parquet")
        pq.write_table(queries, vectors / "queries.parquet")
        np.save(vectors / "card_vectors.npy", np.ones((len(cards), 3), dtype="float32"))
        np.save(vectors / "query_vectors.npy", np.ones((len(queries), 3), dtype="float32"))
        output = tmp_path / split
        build(data, vectors, output, split, customer_dropout=0.5)
        features = pq.read_table(output / "features.parquet")
        assert len(features) > 0
        assert set(FEATURES) <= set(features.column_names)
        assert not any("FUTURE_SECRET" in str(row) for row in features.to_pylist())
        folders.append(output)
    train(*folders, tmp_path / "models", iterations=3)
    report = json.loads((tmp_path / "models/report.json").read_text())
    assert len(report["models"]) == 3


def test_runtime_features_match_training():
    source = (
        Path(__file__).resolve().parents[2] / "backend/src/adapter/repository/ranker/features.py"
    )
    spec = importlib.util.spec_from_file_location("runtime_features", source)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    assert runtime.FEATURES == FEATURES
    for price in (None, 0, 15000):
        args = (
            {"query_text": "Поставка бумаги", "start_price": price},
            {"profile_text": "Бумага для печати", "profile_last_date": "2024-01-01"},
            {"participations": 12, "wins": 4, "mean_log_price": 8.0},
            {"participations": 2.5, "wins": 0.5},
            {},
            [0.8, 2.0, 0.03, 2, 1, 301],
            date(2024, 12, 1),
            3,
        )
        np.testing.assert_allclose(runtime.feature_row(*args), feature_row(*args), equal_nan=True)
