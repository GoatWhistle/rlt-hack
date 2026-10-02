"""Build labelled top-200 retrieval pools under the original temporal splits."""

import argparse
import hashlib
import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from rlt_ml.common import write_json
from rlt_ml.reranking.features import FEATURES, feature_row
from rlt_ml.retrieval import lexical_index


def unique(scores, cards, positive=False):
    found = {}
    for position in np.argsort(-scores, kind="stable"):
        if positive and scores[position] <= 0:
            break
        found.setdefault(cards[position]["supplier_inn"], int(position))
        if len(found) == 300:
            break
    return found


def build(data, vectors, out, split, customer_dropout=0.0):
    out.mkdir(parents=True, exist_ok=True)
    folder = data / split
    cards = pq.read_table(vectors / "cards.parquet").to_pylist()
    queries = pq.read_table(vectors / "queries.parquet").to_pylist()
    matrix = np.load(vectors / "card_vectors.npy", mmap_mode="r")
    query_vectors = np.load(vectors / "query_vectors.npy", mmap_mode="r")
    matrix_norm = np.linalg.norm(matrix, axis=1)
    vectorizer, lexical = lexical_index([card["profile_text"] for card in cards], "bm25")
    suppliers = {
        row["supplier_inn"]: row
        for row in pq.read_table(folder / "supplier_stats.parquet").to_pylist()
    }
    categories = {
        (row["supplier_inn"], row["category"]): row
        for row in pq.read_table(folder / "category_stats.parquet").to_pylist()
    }
    customers = {
        (row["supplier_inn"], row["customer_inn"]): row
        for row in pq.read_table(folder / "customer_stats.parquet").to_pylist()
    }
    by_customer, positions = defaultdict(list), defaultdict(list)
    for row in customers.values():
        by_customer[row["customer_inn"]].append(row)
    for entries in by_customer.values():
        entries.sort(key=lambda row: (-row["wins"], -row["participations"], row["supplier_inn"]))
    for i, card in enumerate(cards):
        positions[card["supplier_inn"]].append(i)
    participants, winners = defaultdict(set), defaultdict(set)
    for row in pq.read_table(folder / "targets.parquet").to_pylist():
        participants[row["lot_id"]].add(row["supplier_inn"])
        if row["is_winner"] and not row["label_conflict"]:
            winners[row["lot_id"]].add(row["supplier_inn"])
    cutoff = date.fromisoformat(
        {"train": "2024-06-01", "validation": "2024-12-01", "test": "2025-06-01"}[split]
    )
    rng = np.random.default_rng(42)
    writer, report = None, []
    started = time.monotonic()
    try:
        for number, original in enumerate(queries):
            query = dict(original)
            if rng.random() < customer_dropout:
                query["customer_inn"] = None
                query["start_price"] = None
            vector = query_vectors[number]
            dense = matrix @ vector / matrix_norm / np.linalg.norm(vector)
            lexical_scores = (
                (lexical @ vectorizer.transform([query["query_text"]]).sign().T).toarray().ravel()
            )
            dense_order, lexical_order = unique(dense, cards), unique(lexical_scores, cards, True)
            customer_order = [
                row["supplier_inn"]
                for row in by_customer.get(query.get("customer_inn"), [])
                if row["supplier_inn"] in positions
            ][:100]
            ranks = [
                {inn: rank for rank, inn in enumerate(order, 1)}
                for order in (dense_order, lexical_order, customer_order)
            ]
            scores = defaultdict(float)
            for weight, ranking in zip((1.0, 1.0, 0.5), ranks, strict=True):
                for inn, rank in ranking.items():
                    scores[inn] += weight / (60 + rank)
            selected = sorted(scores, key=lambda inn: (-scores[inn], inn))[:200]
            winner_set = winners[query["lot_id"]]
            winner = next(iter(winner_set)) if len(winner_set) == 1 else None
            records = []
            for rank, inn in enumerate(selected, 1):
                position = dense_order.get(inn)
                if position is None:
                    options = positions[inn]
                    position = options[int(np.argmax(dense[options]))]
                card = cards[position]
                raw = [
                    dense[position],
                    lexical_scores[position],
                    scores[inn],
                    *(ranking.get(inn, 301) for ranking in ranks),
                ]
                values = feature_row(
                    query,
                    card,
                    suppliers.get(inn, {}),
                    categories.get((inn, card["category"]), {}),
                    customers.get((inn, query.get("customer_inn")), {}),
                    raw,
                    cutoff,
                    len(positions[inn]),
                )
                records.append(
                    {
                        "lot_id": str(query["lot_id"]),
                        "supplier_inn": inn,
                        "rank": rank,
                        "participant": int(inn in participants[query["lot_id"]]),
                        "winner": int(inn == winner),
                        **dict(zip(FEATURES, values, strict=True)),
                    }
                )
            table = pa.Table.from_pylist(records)
            if writer is None:
                writer = pq.ParquetWriter(
                    out / "features.parquet", table.schema, compression="zstd"
                )
            writer.write_table(table)
            report.append(
                {
                    "lot_id": query["lot_id"],
                    "candidate_inns": selected,
                    "participants": sorted(participants[query["lot_id"]]),
                    "winner_inn": winner,
                    "procedure_id": query.get("procedure_id"),
                }
            )
            if (number + 1) % 100 == 0:
                print(
                    f"candidates {number + 1}/{len(queries)} {time.monotonic() - started:.1f}s",
                    flush=True,
                )
    finally:
        if writer:
            writer.close()
    with (out / "predictions.jsonl").open("w") as stream:
        for row in report:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_json(
        out / "metadata.json",
        {
            "split": split,
            "features": list(FEATURES),
            "queries": len(queries),
            "query_sample_sha256": hashlib.sha256(
                json.dumps([q["lot_id"] for q in queries]).encode()
            ).hexdigest(),
            "customer_dropout": customer_dropout,
            "seconds": time.monotonic() - started,
        },
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split", choices=["train", "validation", "test"], required=True)
    parser.add_argument("--customer-dropout", type=float, default=0.0)
    args = parser.parse_args()
    build(args.data, args.vectors, args.out, args.split, args.customer_dropout)


if __name__ == "__main__":
    main()
