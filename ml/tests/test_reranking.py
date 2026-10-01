import importlib.util
import json
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from catboost import CatBoostRanker, Pool

from rlt_ml.common import sha256
from rlt_ml.reranking.candidates import build
from rlt_ml.reranking.evaluate import evaluate
from rlt_ml.reranking.export import export
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


def test_fixed_model_evaluation_and_export(tmp_path):
    models, candidates, vectors, data = [
        tmp_path / name for name in ("models", "candidates", "vectors", "data")
    ]
    for folder in (models, candidates, vectors, data / "validation"):
        folder.mkdir(parents=True)
    values = np.zeros((4, len(FEATURES)))
    values[:, 0] = [1, 0, 1, 0]
    model = CatBoostRanker(
        iterations=10,
        depth=2,
        loss_function="QuerySoftMax",
        verbose=False,
        thread_count=1,
        allow_writing_files=False,
    )
    model.fit(
        Pool(values, [1, 0, 1, 0], group_id=["x", "x", "y", "y"], feature_names=list(FEATURES))
    )
    model.save_model(str(models / "ranker.cbm"))
    (models / "manifest.json").write_text(
        json.dumps(
            {
                "model_sha256": sha256(models / "ranker.cbm"),
                "selected": "synthetic",
                "features": list(FEATURES),
            }
        )
    )
    rows = []
    for i, (lot, inn) in enumerate([("x", "a"), ("x", "b"), ("y", "a"), ("y", "b")]):
        rows.append(
            {
                "lot_id": lot,
                "supplier_inn": inn,
                "rank": 2 - i % 2,
                **dict(zip(FEATURES, values[i], strict=True)),
            }
        )
    pq.write_table(pa.Table.from_pylist(rows), candidates / "features.parquet")
    (candidates / "metadata.json").write_text(json.dumps({"split": "test"}))
    (candidates / "predictions.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "lot_id": lot,
                    "candidate_inns": ["b", "a"],
                    "participants": ["a"],
                    "winner_inn": "a",
                    "procedure_id": lot,
                }
            )
            for lot in ("x", "y")
        )
    )
    evaluate(models, candidates, models / "test-report.json")
    result = json.loads((models / "test-report.json").read_text())
    assert result["accepted"] and result["winner_mrr_delta"] == 0.5
    assert result["winner_mrr_delta_cluster_ci95"] == [0.5, 0.5]
    for name in ("cards.parquet", "supplier_stats.parquet", "category_stats.parquet"):
        pq.write_table(
            pa.Table.from_pylist([{"supplier_inn": "a", "category": "paper"}]),
            (vectors if name == "cards.parquet" else data / "validation") / name,
        )
    np.save(vectors / "card_vectors.npy", np.ones((1, 2560), dtype="float32"))
    (vectors / "vectors.json").write_text(
        json.dumps(
            {
                "model": "Qwen/Qwen3-Embedding-4B",
                "split": "validation",
                "revision": "synthetic",
                "cards": 1,
                "instruction": "synthetic",
            }
        )
    )
    export(models, vectors, data, tmp_path / "runtime")
    assert (tmp_path / "runtime/ranker/runtime.json").exists()
    result["accepted"] = False
    (models / "test-report.json").write_text(json.dumps(result))
    with pytest.raises(ValueError, match="held-out"):
        export(models, vectors, data, tmp_path / "rejected")
