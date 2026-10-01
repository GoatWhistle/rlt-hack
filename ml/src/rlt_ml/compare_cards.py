"""Парное сравнение retrieval-прогонов с кластерным bootstrap по процедурам."""

import argparse
import json
from pathlib import Path

import numpy as np

from rlt_ml.common import write_json


def _metrics(rows: list[dict], candidates_key: str = "candidate_inns") -> dict[str, np.ndarray]:
    recall, winner_recall, mrr = [], [], []
    for row in rows:
        candidates = row[candidates_key]
        if candidates is None:
            raise ValueError(f"Нет списка кандидатов {candidates_key}")
        participants = set(row["participants"])
        recall.append(len(participants.intersection(candidates)) / len(participants)
                      if participants else np.nan)
        winner = row["winner_inn"]
        winner_recall.append(float(winner in candidates) if winner else np.nan)
        mrr.append(1 / (candidates.index(winner) + 1)
                   if winner and winner in candidates else (0.0 if winner else np.nan))
    return {"recall_at_100": np.asarray(recall),
            "winner_recall_at_100": np.asarray(winner_recall),
            "winner_mrr_at_100": np.asarray(mrr)}


def _mean(values: np.ndarray) -> float | None:
    return float(np.nanmean(values)) if np.isfinite(values).any() else None


def compare(predictions: dict[str, Path], baseline: str = "A", replicates: int = 2000,
            seed: int = 42) -> dict:
    loaded = {name: [json.loads(line) for line in path.open() if line.strip()]
              for name, path in predictions.items()}
    if baseline not in loaded:
        raise ValueError(f"Нет baseline {baseline}")
    base_rows = loaded[baseline]
    lot_ids = [row["lot_id"] for row in base_rows]
    groups = [row["procedure_group"] for row in base_rows]
    for name, rows in loaded.items():
        if [row["lot_id"] for row in rows] != lot_ids:
            raise ValueError(f"Набор/порядок запросов отличается у {name}")
        if [row["procedure_group"] for row in rows] != groups:
            raise ValueError(f"Группы процедур отличаются у {name}")
        for index, row in enumerate(rows):
            if row["participants"] != base_rows[index]["participants"] or row["winner_inn"] != base_rows[index]["winner_inn"]:
                raise ValueError(f"Разметка различается у {name}, запрос {index}")

    unique_groups = np.asarray(sorted(set(groups)))
    group_indices = {key: np.flatnonzero(np.asarray(groups) == key) for key in unique_groups}
    rng = np.random.default_rng(seed)
    summary, comparisons = {}, {}
    channels = {"hybrid": "candidate_inns", "dense_only": "dense_candidate_inns"}
    metrics = {
        channel: {name: _metrics(rows, key) for name, rows in loaded.items()}
        for channel, key in channels.items()
    }
    for channel, channel_metrics in metrics.items():
        summary[channel] = {}
        comparisons[channel] = {}
        for name, values in channel_metrics.items():
            summary[channel][name] = {metric: _mean(array) for metric, array in values.items()}
        base_metrics = channel_metrics[baseline]
        for name, values in channel_metrics.items():
            if name == baseline:
                continue
            comparisons[channel][name] = {}
            for metric, base_values in base_metrics.items():
                candidate_values = values[metric]
                paired = np.isfinite(base_values) & np.isfinite(candidate_values)
                delta = candidate_values - base_values
                observed = _mean(delta[paired])
                samples = np.empty(replicates, dtype=np.float64)
                for replicate in range(replicates):
                    selected = rng.choice(unique_groups, len(unique_groups), replace=True)
                    indices = np.concatenate([group_indices[group] for group in selected])
                    valid = paired[indices]
                    samples[replicate] = np.mean(delta[indices][valid]) if valid.any() else np.nan
                low, high = np.nanpercentile(samples, [2.5, 97.5])
                comparisons[channel][name][metric] = {
                    "delta": observed, "ci95": [float(low), float(high)],
                    "paired_queries": int(paired.sum()),
                }
    return {"baseline": baseline, "queries": len(base_rows),
            "procedure_groups": len(unique_groups), "replicates": replicates,
            "seed": seed, "metrics": summary, "paired_deltas": comparisons,
            "bootstrap": "paired percentile bootstrap resampling procedure_group clusters"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--variants", default="ABCD",
                        help="Имена вариантов из A, B, C, D, например AD")
    parser.add_argument("--replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    variants = list(dict.fromkeys(args.variants.upper()))
    if not variants or any(name not in "ABCD" for name in variants):
        parser.error("variants должны содержать буквы из A, B, C, D")
    paths = {name: args.predictions_dir / name / "predictions.jsonl" for name in variants}
    report = compare(paths, replicates=args.replicates, seed=args.seed)
    write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
