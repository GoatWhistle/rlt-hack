"""Train on retrieved candidates and select only on the development split."""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from catboost import CatBoostRanker, Pool

from rlt_ml.common import sha256, write_json
from rlt_ml.reranking.features import FEATURES


def metrics(rows, orders):
    winners, reciprocal, participants, recalls = [], [], [], []
    for row in rows:
        order = orders[row["lot_id"]]
        known = set(row["participants"])
        participants.append(bool(known & set(order[:10])))
        if known:
            recalls.append(len(known & set(order[:10])) / len(known))
        if row["winner_inn"]:
            rank = order.index(row["winner_inn"]) + 1 if row["winner_inn"] in order else 0
            winners.append(rank)
            reciprocal.append(1 / rank if rank else 0.0)
    ranks = np.asarray(winners)
    return {
        "queries": len(rows),
        "winner_queries": len(ranks),
        "winner_hit_1": float(np.mean(ranks == 1)),
        "winner_hit_5": float(np.mean((ranks > 0) & (ranks <= 5))),
        "winner_hit_10": float(np.mean((ranks > 0) & (ranks <= 10))),
        "winner_hit_20": float(np.mean((ranks > 0) & (ranks <= 20))),
        "winner_recall_200": float(np.mean(ranks > 0)),
        "winner_mrr": float(np.mean(reciprocal)),
        "bidder_hit_10": float(np.mean(participants)),
        "participant_recall_10": float(np.mean(recalls)),
    }


def orders(frame, scores):
    frame = frame[["lot_id", "supplier_inn"]].copy()
    frame["score"] = scores
    return {
        lot: group.sort_values(
            ["score", "supplier_inn"], ascending=[False, True]
        ).supplier_inn.tolist()
        for lot, group in frame.groupby("lot_id", sort=False)
    }


def pool(frame, graded):
    labels = frame["participant"] + frame["winner"] if graded else frame["winner"]
    return Pool(
        frame[list(FEATURES)],
        labels.to_numpy(),
        group_id=frame.lot_id.to_numpy(),
        feature_names=list(FEATURES),
    )


def train(train_dir, validation_dir, out, iterations=600, text_validation_dir=None):
    out.mkdir(parents=True, exist_ok=False)
    training = (
        pq.read_table(train_dir / "features.parquet").to_pandas().sort_values(["lot_id", "rank"])
    )
    validation = (
        pq.read_table(validation_dir / "features.parquet")
        .to_pandas()
        .sort_values(["lot_id", "rank"])
    )
    rows = [
        json.loads(line) for line in (validation_dir / "predictions.jsonl").read_text().splitlines()
    ]
    baseline = {row["lot_id"]: row["candidate_inns"] for row in rows}
    report = {
        "features": list(FEATURES),
        "baseline": metrics(rows, baseline),
        "models": {},
        "train_queries": training.lot_id.nunique(),
        "validation_metadata": json.loads((validation_dir / "metadata.json").read_text()),
        "limitations": [
            "Historical participation is incomplete relevance supervision; missing bidders are weak negatives.",
            "Scores are not calibrated probabilities of winning or delivery quality.",
            "Validation selects the model; final test remains separate.",
        ],
    }
    text_frame, text_rows = None, None
    if text_validation_dir:
        text_frame = (
            pq.read_table(text_validation_dir / "features.parquet")
            .to_pandas()
            .sort_values(["lot_id", "rank"])
        )
        text_rows = [
            json.loads(line)
            for line in (text_validation_dir / "predictions.jsonl").read_text().splitlines()
        ]
        if [row["lot_id"] for row in text_rows] != [row["lot_id"] for row in rows]:
            raise ValueError("Text and full validation must use the same queries")
        report["text_baseline"] = metrics(
            text_rows, {row["lot_id"]: row["candidate_inns"] for row in text_rows}
        )
    best = report.get("text_baseline", report["baseline"])["winner_mrr"]
    chosen = None
    for name, loss, graded in [
        ("softmax_winner", "QuerySoftMax", False),
        ("softmax_participants", "QuerySoftMax", True),
        ("yetirank_participants", "YetiRank", True),
    ]:
        label = "participant" if graded else "winner"
        selected = training[training.groupby("lot_id")[label].transform("sum") > 0]
        eval_rows = validation[validation.groupby("lot_id")[label].transform("sum") > 0]
        started = time.monotonic()
        model = CatBoostRanker(
            loss_function=loss,
            iterations=iterations,
            depth=6,
            learning_rate=0.05,
            l2_leaf_reg=10,
            random_seed=42,
            thread_count=4,
            verbose=100,
            allow_writing_files=False,
        )
        model.fit(
            pool(selected, graded), eval_set=pool(eval_rows, graded), early_stopping_rounds=80
        )
        predicted = orders(validation, model.predict(validation[list(FEATURES)]))
        score = metrics(rows, predicted)
        score.update(
            seconds=time.monotonic() - started,
            trees=model.tree_count_,
            train_groups=selected.lot_id.nunique(),
        )
        model.save_model(str(out / f"{name}.cbm"))
        importance = model.get_feature_importance(type="PredictionValuesChange")
        score["importance"] = {
            key: float(value) for key, value in zip(FEATURES, importance, strict=True)
        }
        selection_score = score
        selection_baseline = report["baseline"]
        if text_frame is not None:
            score["text_only"] = metrics(
                text_rows, orders(text_frame, model.predict(text_frame[list(FEATURES)]))
            )
            selection_score = score["text_only"]
            selection_baseline = report["text_baseline"]
        report["models"][name] = score
        if (
            selection_score["winner_mrr"] > best
            and selection_score["bidder_hit_10"] >= selection_baseline["bidder_hit_10"] - 0.01
            and score["winner_mrr"] >= report["baseline"]["winner_mrr"]
            and score["bidder_hit_10"] >= report["baseline"]["bidder_hit_10"] - 0.01
        ):
            best, chosen = selection_score["winner_mrr"], name
        write_json(out / "report.json", report)
    report["selected"] = chosen
    if chosen:
        source = out / f"{chosen}.cbm"
        (out / "ranker.cbm").write_bytes(source.read_bytes())
        write_json(
            out / "manifest.json",
            {
                "schema_version": 1,
                "model": "Qwen/Qwen3-Embedding-4B",
                "features": list(FEATURES),
                "model_sha256": sha256(out / "ranker.cbm"),
                "selection": "validation",
                "selected": chosen,
                "baseline": report["baseline"],
                "validation": report["models"][chosen],
            },
        )
    write_json(out / "report.json", report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--text-validation", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=600)
    args = parser.parse_args()
    train(args.train, args.validation, args.out, args.iterations, args.text_validation)


if __name__ == "__main__":
    main()
