"""Resumable Qwen 4B vectors for temporally isolated reranker datasets."""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import torch

from rlt_ml.common import sha256
from rlt_ml.retrieval import torch_float32_to_numpy
from rlt_ml.text_encoder import TextEncoder

MODEL = "Qwen/Qwen3-Embedding-4B"
INSTRUCTION = "Given a Russian procurement notice, retrieve supplier activity profiles relevant to fulfilling this procurement."


def checkpoint(path, payload):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False))
    temporary.replace(path)


def encode(texts, output, encoder, *, query, batch_size, cached=None):
    progress = output.with_suffix(".progress.json")
    fingerprint = hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest()
    completed = 0
    if progress.exists():
        state = json.loads(progress.read_text())
        if state["texts_sha256"] != fingerprint:
            raise ValueError("Changed inputs cannot reuse vector checkpoint")
        completed = state["completed"]
    matrix = np.lib.format.open_memmap(
        output, mode="r+" if output.exists() else "w+", dtype="float32", shape=(len(texts), 2560)
    )
    started = time.monotonic()
    while completed < len(texts):
        end = min(completed + batch_size, len(texts))
        missing = []
        for index in range(completed, end):
            match = cached.get(texts[index]) if cached is not None else None
            if match is None:
                missing.append(index)
            else:
                matrix[index] = match
        if missing:
            try:
                with torch.inference_mode():
                    value = encoder([texts[index] for index in missing], query=query)
                    matrix[missing] = torch_float32_to_numpy(value)
            except torch.cuda.OutOfMemoryError:
                if batch_size == 1:
                    raise
                batch_size = max(1, batch_size // 2)
                torch.cuda.empty_cache()
                continue
        completed = end
        matrix.flush()
        checkpoint(
            progress,
            {
                "completed": completed,
                "total": len(texts),
                "texts_sha256": fingerprint,
                "model": MODEL,
                "batch_size": batch_size,
            },
        )
        if completed % 100 == 0 or completed == len(texts):
            print(
                f"{output.name}: {completed}/{len(texts)} {time.monotonic() - started:.1f}s",
                flush=True,
            )
    return matrix


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split", choices=["train", "validation", "test"], required=True)
    parser.add_argument("--queries", type=int, default=4000)
    parser.add_argument("--reuse", type=Path)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()
    if args.out.exists() and not args.out.is_dir():
        raise ValueError("Output must be a directory")
    args.out.mkdir(parents=True, exist_ok=True)
    folder = args.data / args.split
    cards = pq.read_table(folder / "cards.parquet").to_pylist()
    with duckdb.connect() as con:
        queries = con.execute(
            "SELECT * FROM read_parquet(?) WHERE participant_count > 0 ORDER BY hash(lot_id, 42) LIMIT ?",
            [str(folder / "queries.parquet"), args.queries],
        ).to_arrow_table()
    pq.write_table(queries, args.out / "queries.parquet")
    pq.write_table(pa.Table.from_pylist(cards), args.out / "cards.parquet")
    cached = {}
    if args.reuse:
        previous = pq.read_table(args.reuse / "cards.parquet").to_pylist()
        vectors = np.load(args.reuse / "card_vectors.npy", mmap_mode="r")
        if vectors.shape != (len(previous), 2560):
            raise ValueError("Incompatible cached 4B vectors")
        cached = {card["profile_text"]: vectors[i] for i, card in enumerate(previous)}
    torch.set_num_threads(2)
    torch.cuda.set_per_process_memory_fraction(0.90)
    encoder = TextEncoder(MODEL, 256, INSTRUCTION, card_max_length=512)
    encoder.model.eval()
    encode(
        [card["profile_text"] for card in cards],
        args.out / "card_vectors.npy",
        encoder,
        query=False,
        batch_size=args.batch_size,
        cached=cached,
    )
    encode(
        queries.column("query_text").to_pylist(),
        args.out / "query_vectors.npy",
        encoder,
        query=True,
        batch_size=args.batch_size,
    )
    checkpoint(
        args.out / "vectors.json",
        {
            "model": MODEL,
            "revision": encoder.base_revision,
            "query_max_length": 256,
            "card_max_length": 512,
            "instruction": INSTRUCTION,
            "split": args.split,
            "queries": len(queries),
            "cards": len(cards),
            "cards_sha256": sha256(args.out / "cards.parquet"),
            "queries_sha256": sha256(args.out / "queries.parquet"),
            "gpu_peak_bytes": torch.cuda.max_memory_allocated(),
            "source_git_revision": os.getenv("RLT_SOURCE_REVISION", ""),
        },
    )


if __name__ == "__main__":
    main()
