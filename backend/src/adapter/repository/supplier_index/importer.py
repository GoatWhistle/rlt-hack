import asyncio
import hashlib
import json
from pathlib import Path

import numpy as np
from pyarrow import parquet

from src.adapter.repository.supplier_index.protocols import SqlGateway


def read_artifacts(directory: Path) -> tuple[dict, list[dict], np.ndarray]:
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if name not in {"card_vectors.npy", "cards.parquet", "report.json"}:
            continue
        with (directory / name).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError("Index checksum mismatch")
    vectors = np.load(directory / "card_vectors.npy", mmap_mode="r", allow_pickle=False)
    cards = parquet.read_table(directory / "cards.parquet").to_pylist()
    if list(vectors.shape) != manifest["shape"] or len(cards) != len(vectors):
        raise ValueError("Index dimensions mismatch")
    if len({card["card_id"] for card in cards}) != len(cards):
        raise ValueError("Duplicate card IDs")
    return manifest, cards, vectors


async def import_index(gateway: SqlGateway, database: str, directory: Path) -> dict:
    manifest, cards, vectors = await asyncio.to_thread(read_artifacts, directory)
    index_id = manifest["files"]["card_vectors.npy"]
    table = f"{database}.supplier_profile_embeddings"
    existing = await gateway.select(
        f"SELECT card_id FROM {table} FINAL WHERE index_id = {{index:String}}",
        {"index": index_id},
    )
    seen = {row[0] for row in existing}
    columns = (
        "index_id",
        "card_id",
        "supplier_inn",
        "category",
        "profile_text",
        "model",
        "model_revision",
        "dimensions",
        "embedding",
        "content_hash",
    )
    for start in range(0, len(cards), 128):
        rows = await asyncio.to_thread(batch_rows, manifest, cards, vectors, seen, start, index_id)
        await gateway.insert(table, columns, rows)
    counts = await gateway.select(
        f"SELECT count(), uniqExact(supplier_inn), min(length(embedding)), "
        f"max(length(embedding)) FROM {table} FINAL WHERE index_id = {{index:String}}",
        {"index": index_id},
    )
    expected_suppliers = len({card["supplier_inn"] for card in cards})
    if counts != [(len(cards), expected_suppliers, vectors.shape[1], vectors.shape[1])]:
        raise ValueError("Imported index counts mismatch")
    await gateway.insert(
        f"{database}.supplier_profile_indexes",
        (
            "index_id",
            "model",
            "model_revision",
            "dimensions",
            "card_count",
            "supplier_count",
            "vectors_sha256",
            "cards_sha256",
            "query_instruction",
        ),
        [
            (
                index_id,
                manifest["model"],
                manifest["revision"],
                vectors.shape[1],
                len(cards),
                expected_suppliers,
                index_id,
                manifest["files"]["cards.parquet"],
                manifest["query_instruction"],
            )
        ],
    )
    return {
        "index_id": index_id,
        "cards": len(cards),
        "suppliers": expected_suppliers,
        "already_present": len(seen),
    }


def batch_rows(manifest, cards, vectors, seen, start, index_id):
    result = []
    for position in range(start, min(start + 128, len(cards))):
        card = cards[position]
        if card["card_id"] in seen:
            continue
        vector = vectors[position]
        if not np.isfinite(vector).all() or not np.any(vector):
            raise ValueError("Invalid vector")
        result.append(
            (
                index_id,
                card["card_id"],
                card["supplier_inn"],
                card["category"],
                card["profile_text"],
                manifest["model"],
                manifest["revision"],
                len(vector),
                vector.tolist(),
                hashlib.sha256(card["profile_text"].encode()).hexdigest(),
            )
        )
    return result
