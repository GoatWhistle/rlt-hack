"""Compare offline ranking with the actual serving adapter, on the server only."""

import argparse
import asyncio
import json
import os
import resource
import tempfile
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from catboost import CatBoostRanker
from src.adapter.repository.ranker.model import CandidateRanker
from src.adapter.repository.supplier_index.index import FileSupplierIndex

from rlt_ml.common import sha256, write_json
from rlt_ml.reranking.features import FEATURES


async def check(data, vectors, candidates, models, out, count):
    started = time.monotonic()
    metadata = json.loads((vectors / "vectors.json").read_text())
    frame = pq.read_table(candidates / "features.parquet").to_pandas()
    queries = pq.read_table(vectors / "queries.parquet").to_pylist()[:count]
    query_vectors = np.load(vectors / "query_vectors.npy", mmap_mode="r")
    model = CatBoostRanker()
    model.load_model(str(models / "ranker.cbm"))
    matches, maximum_delta = 0, 0.0
    with tempfile.TemporaryDirectory(prefix="rlt-serving-check-") as temporary:
        root = Path(temporary)
        for name in ("cards.parquet", "card_vectors.npy"):
            os.symlink(vectors / name, root / name)
        write_json(root / "report.json", {})
        write_json(
            root / "manifest.json",
            {
                "query_instruction": metadata["instruction"],
                "shape": [metadata["cards"], 2560],
                "files": {
                    name: sha256(root / name)
                    for name in ("cards.parquet", "card_vectors.npy", "report.json")
                },
            },
        )
        runtime = root / "ranker"
        runtime.mkdir()
        os.symlink(models / "ranker.cbm", runtime / "ranker.cbm")
        for name in ("supplier_stats.parquet", "category_stats.parquet"):
            os.symlink(data / metadata["split"] / name, runtime / name)
        write_json(
            runtime / "runtime.json",
            {
                "features": list(FEATURES),
                "model": metadata["model"],
                "cards_sha256": sha256(root / "cards.parquet"),
                "history_before": {
                    "validation": "2024-12-01",
                    "test": "2025-06-01",
                }[metadata["split"]],
                "files": {
                    name: sha256(runtime / name)
                    for name in ("ranker.cbm", "supplier_stats.parquet", "category_stats.parquet")
                },
            },
        )
        index = FileSupplierIndex(root)
        await index.initialize()
        ranker = CandidateRanker(runtime)
        await ranker.initialize(index.cards, sha256(root / "cards.parquet"))
        index.ranker = ranker
        for i, query in enumerate(queries):
            group = frame[frame.lot_id == str(query["lot_id"])].copy()
            group["prediction"] = model.predict(group[list(FEATURES)], thread_count=2)
            expected = group.sort_values(
                ["prediction", "supplier_inn"], ascending=[False, True]
            ).head(10)
            actual = await index.search(query["query_text"], query_vectors[i].tolist(), 10)
            matches += [item.inn for item in actual] == expected.supplier_inn.tolist()
            expected_scores = dict(zip(group.supplier_inn, group.prediction, strict=True))
            maximum_delta = max(
                maximum_delta, max(abs(item.score - expected_scores[item.inn]) for item in actual)
            )
    report = {
        "queries": len(queries),
        "identical_top10": matches,
        "max_score_delta": maximum_delta,
        "seconds": time.monotonic() - started,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "model_sha256": sha256(models / "ranker.cbm"),
        "passed": matches == len(queries) and maximum_delta < 1e-8,
    }
    write_json(out, report)
    print(json.dumps(report), flush=True)
    if not report["passed"]:
        raise ValueError("Serving differs from offline evaluation")


def main():
    parser = argparse.ArgumentParser()
    for name in ("data", "vectors", "candidates", "models", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--queries", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(
        check(args.data, args.vectors, args.candidates, args.models, args.out, args.queries)
    )


if __name__ == "__main__":
    main()
