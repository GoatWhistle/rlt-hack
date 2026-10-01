"""Evaluate a fixed selected model on held-out retrieval groups."""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from catboost import CatBoostRanker

from rlt_ml.common import sha256, write_json
from rlt_ml.reranking.features import FEATURES
from rlt_ml.reranking.train import metrics, orders


def evaluate(models, candidates, out):
    selection = json.loads((models / "manifest.json").read_text())
    if sha256(models / "ranker.cbm") != selection["model_sha256"]:
        raise ValueError("Selected model changed before test")
    metadata = json.loads((candidates / "metadata.json").read_text())
    frame = (
        pq.read_table(candidates / "features.parquet").to_pandas().sort_values(["lot_id", "rank"])
    )
    rows = [
        json.loads(line) for line in (candidates / "predictions.jsonl").read_text().splitlines()
    ]
    baseline = {row["lot_id"]: row["candidate_inns"] for row in rows}
    model = CatBoostRanker()
    model.load_model(str(models / "ranker.cbm"))
    started = time.monotonic()
    predictions = model.predict(frame[list(FEATURES)], thread_count=4)
    seconds = time.monotonic() - started
    ranked = orders(frame, predictions)
    before, after = metrics(rows, baseline), metrics(rows, ranked)
    clusters = {}
    for row in rows:
        winner = row["winner_inn"]
        if not winner:
            continue
        values = []
        for ranking in (baseline, ranked):
            order = ranking[row["lot_id"]]
            values.append(1 / (order.index(winner) + 1) if winner in order else 0.0)
        group = row.get("procedure_id") or row["lot_id"]
        clusters.setdefault(group, []).append(values[1] - values[0])
    groups = list(clusters.values())
    sums = np.array([sum(group) for group in groups])
    sizes = np.array([len(group) for group in groups])
    rng = np.random.default_rng(42)
    boot = []
    for _ in range(2000):
        sample = rng.integers(0, len(groups), size=len(groups))
        boot.append(float(sums[sample].sum() / sizes[sample].sum()))
    interval = np.quantile(boot, [0.025, 0.975]).tolist()
    report = {
        "split": metadata["split"],
        "model_sha256": selection["model_sha256"],
        "selected": selection["selected"],
        "metadata": metadata,
        "baseline": before,
        "ranker": after,
        "winner_mrr_delta": after["winner_mrr"] - before["winner_mrr"],
        "winner_mrr_delta_cluster_ci95": interval,
        "bootstrap_procedures": len(groups),
        "prediction_seconds": seconds,
        "milliseconds_per_query": 1000 * seconds / len(rows),
        "accepted": metadata["split"] == "test"
        and after["winner_mrr"] > before["winner_mrr"]
        and interval[0] > 0
        and after["bidder_hit_10"] >= before["bidder_hit_10"] - 0.01,
        "limitations": [
            "Participation labels are incomplete relevance labels.",
            "Tree scores are not probabilities; timing excludes retrieval and encoding.",
        ],
    }
    write_json(out, report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    for name in ("models", "candidates", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.models, args.candidates, args.out)


if __name__ == "__main__":
    main()
