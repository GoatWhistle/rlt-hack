"""Export immutable, checksum-verified inference artifacts outside Git."""

import argparse
import json
import shutil
from pathlib import Path

from rlt_ml.common import sha256, write_json
from rlt_ml.reranking.features import FEATURES


def export(models: Path, vectors: Path, data: Path, out: Path):
    manifest = json.loads((models / "manifest.json").read_text())
    evaluation = json.loads((models / "test-report.json").read_text())
    if not evaluation["accepted"]:
        raise ValueError("The fixed model did not pass held-out evaluation")
    if (
        manifest["features"] != list(FEATURES)
        or sha256(models / "ranker.cbm") != manifest["model_sha256"]
    ):
        raise ValueError("Model artifact differs from selection")
    if evaluation["model_sha256"] != manifest["model_sha256"] or evaluation["split"] != "test":
        raise ValueError("Evaluation belongs to a different model or split")
    vector_metadata = json.loads((vectors / "vectors.json").read_text())
    if vector_metadata["model"] != "Qwen/Qwen3-Embedding-4B" or vector_metadata["split"] not in {
        "validation",
        "test",
    }:
        raise ValueError("Runtime snapshot must use evaluated 4B history")
    split = vector_metadata["split"]
    before = {"validation": "2024-12-01", "test": "2025-06-01"}[split]
    out.mkdir(parents=True, exist_ok=False)
    for name in ("cards.parquet", "card_vectors.npy"):
        shutil.copyfile(vectors / name, out / name)
    write_json(
        out / "report.json", {"selection": manifest, "test": evaluation, "vectors": vector_metadata}
    )
    write_json(
        out / "manifest.json",
        {
            "model": vector_metadata["model"],
            "revision": vector_metadata["revision"],
            "shape": [vector_metadata["cards"], 2560],
            "query_instruction": vector_metadata["instruction"],
            "history_before": before,
            "files": {
                name: sha256(out / name)
                for name in ("cards.parquet", "card_vectors.npy", "report.json")
            },
        },
    )
    runtime = out / "ranker"
    runtime.mkdir()
    shutil.copyfile(models / "ranker.cbm", runtime / "ranker.cbm")
    for name in ("supplier_stats.parquet", "category_stats.parquet", "customer_stats.parquet"):
        shutil.copyfile(data / split / name, runtime / name)
    write_json(
        runtime / "runtime.json",
        {
            "features": list(FEATURES),
            "cards_sha256": sha256(out / "cards.parquet"),
            "model": vector_metadata["model"],
            "history_before": before,
            "files": {
                name: sha256(runtime / name)
                for name in (
                    "ranker.cbm",
                    "supplier_stats.parquet",
                    "category_stats.parquet",
                    "customer_stats.parquet",
                )
            },
            "evaluation": evaluation,
        },
    )


def main():
    parser = argparse.ArgumentParser()
    for name in ("models", "vectors", "data", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    export(args.models, args.vectors, args.data, args.out)


if __name__ == "__main__":
    main()
