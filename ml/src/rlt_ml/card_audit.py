"""Измерение обрезки карточек токенизатором энкодера."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as parquet
from transformers import AutoTokenizer

from rlt_ml.common import revision, sha256, write_json


def _percentiles(values: list[int]) -> dict:
    if not values:
        return {name: None for name in ("p50", "p90", "p95", "p99", "max")}
    quantiles = np.percentile(values, [50, 90, 95, 99])
    return {
        "p50": float(quantiles[0]),
        "p90": float(quantiles[1]),
        "p95": float(quantiles[2]),
        "p99": float(quantiles[3]),
        "max": max(values),
    }


def _history_bucket(count: int) -> str:
    if count <= 1:
        return "1"
    if count <= 5:
        return "2-5"
    if count <= 20:
        return "6-20"
    return "21+"


def _summary(lengths: list[int], limit: int) -> dict:
    total_tokens = sum(lengths)
    truncated = [length for length in lengths if length > limit]
    removed = sum(length - limit for length in truncated)
    return {
        "cards": len(lengths),
        "truncated_cards": len(truncated),
        "truncated_share": len(truncated) / len(lengths) if lengths else None,
        "discarded_tokens": removed,
        "discarded_token_share": removed / total_tokens if total_tokens else None,
        "full_length_tokens": _percentiles(lengths),
        "truncated_length_tokens": _percentiles([min(length, limit) for length in lengths]),
    }


def _subgroup(rows: list[dict], field: str, lengths: list[int], limit: int) -> dict:
    indices: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        indices[str(row.get(field, "unknown"))].append(index)
    return {
        key: _summary([lengths[index] for index in positions], limit)
        for key, positions in sorted(indices.items())
    }


def _mention_counts(mentions: list[dict], visible_ends: list[int], limit: int) -> dict:
    counts = Counter()
    for row in mentions:
        end = visible_ends[row["card_index"]]
        start_char, end_char = int(row["start_char"]), int(row["end_char"])
        if end_char <= end:
            status = "fully_visible"
        elif start_char < end:
            status = "partially_visible"
        else:
            status = "dropped"
        counts[status] += 1
        if int(row["source_char_count"]) > int(row["displayed_char_count"]):
            counts["source_name_shortened_to_200_chars"] += 1
    return {"limit": limit, "mentions": len(mentions), **dict(counts)}


def _review_samples(name: str, rows: list[dict], lengths: list[int], offsets256: list,
                    offsets512: list, mentions_by_card: dict[str, list[dict]]) -> list[dict]:
    order = sorted(range(len(rows)), key=lambda index: (lengths[index], rows[index]["card_id"]))
    if len(order) <= 10:
        selected = order
    else:
        selected = sorted({order[round(q * (len(order) - 1))] for q in np.linspace(0, 1, 10)})
    samples = []
    for index in selected:
        row = rows[index]
        def visible_end(offsets) -> int:
            return max((int(end) for start, end in offsets if end > start), default=0)

        end256 = visible_end(offsets256[index])
        end512 = visible_end(offsets512[index])
        samples.append({
            "variant": name,
            "card_id": row["card_id"],
            "category": row.get("category", "unknown"),
            "example_count": row.get("example_count"),
            "full_tokens": lengths[index],
            "visible_chars_at_256": end256,
            "visible_chars_at_512": end512,
            "text": row["profile_text"],
            "visible_text_at_256": row["profile_text"][:end256],
            "product_mentions": mentions_by_card.get(row["card_id"], []),
        })
    return samples


def audit_cards(variants_dir: Path, data: Path, model: str, model_revision: str,
                out: Path, batch_size: int = 256) -> dict:
    tokenizer = AutoTokenizer.from_pretrained(
        model, revision=model_revision, local_files_only=True
    )
    if not tokenizer.is_fast:
        raise ValueError("Для аудита product spans нужен fast tokenizer с offsets")
    stats_rows = parquet.read_table(data / "validation/supplier_stats.parquet").to_pylist()
    history = {row["supplier_inn"]: int(row["participations"]) for row in stats_rows}
    results, samples = {}, []
    for name in ("A", "B", "C", "D"):
        folder = variants_dir / name
        rows = parquet.read_table(folder / "cards.parquet").to_pylist()
        mention_rows = parquet.read_table(folder / "product_mentions.parquet").to_pylist()
        mentions_by_card: dict[str, list[dict]] = defaultdict(list)
        for item in mention_rows:
            mentions_by_card[item["card_id"]].append(item)
        lengths, offsets256, offsets512 = [], [], []
        for start in range(0, len(rows), batch_size):
            batch = [row["profile_text"] for row in rows[start:start + batch_size]]
            full = tokenizer(batch, add_special_tokens=True, truncation=False,
                             padding=False)["input_ids"]
            at256 = tokenizer(batch, add_special_tokens=True, truncation=True, max_length=256,
                              padding=False, return_offsets_mapping=True)
            at512 = tokenizer(batch, add_special_tokens=True, truncation=True, max_length=512,
                              padding=False, return_offsets_mapping=True)
            lengths.extend(len(value) for value in full)
            offsets256.extend(at256["offset_mapping"])
            offsets512.extend(at512["offset_mapping"])
        history_buckets = [_history_bucket(history.get(row["supplier_inn"], 0)) for row in rows]
        for row, bucket in zip(rows, history_buckets, strict=True):
            row["history_bucket"] = bucket
        limit_results = {}
        for limit, offsets in ((256, offsets256), (512, offsets512)):
            visible_ends = [
                max((int(end) for start, end in value if end > start), default=0)
                for value in offsets
            ]
            indexed_mentions = []
            card_indices = {row["card_id"]: index for index, row in enumerate(rows)}
            for mention in mention_rows:
                if mention["card_id"] in card_indices:
                    indexed_mentions.append({**mention, "card_index": card_indices[mention["card_id"]]})
            limit_results[str(limit)] = {
                "overall": _summary(lengths, limit),
                "by_category": _subgroup(rows, "category", lengths, limit),
                "by_example_count": _subgroup(rows, "example_count", lengths, limit),
                "by_supplier_history": _subgroup(rows, "history_bucket", lengths, limit),
                "product_mentions": _mention_counts(indexed_mentions, visible_ends, limit),
            }
        results[name] = {
            "card_count": len(rows),
            "supplier_count": len({row["supplier_inn"] for row in rows}),
            "max_cards_per_supplier": max(Counter(row["supplier_inn"] for row in rows).values()),
            "cards_sha256": sha256(folder / "cards.parquet"),
            "product_mentions_sha256": sha256(folder / "product_mentions.parquet"),
            "variant_manifest_sha256": sha256(folder / "manifest.json"),
            "limits": limit_results,
        }
        samples.extend(_review_samples(name, rows, lengths, offsets256, offsets512,
                                       mentions_by_card))
    report = {
        "source_git_revision": revision(),
        "model": model,
        "tokenizer_revision": model_revision,
        "tokenizer_is_fast": tokenizer.is_fast,
        "data_manifest_sha256": sha256(data / "manifest.json"),
        "validation_queries_sha256": sha256(data / "validation/queries.parquet"),
        "variants": results,
        "manual_review_sample_count": len(samples),
        "notes": [
            "Token lengths include tokenizer special tokens and are measured without padding.",
            "Discarded-token share is sum(max(full_length-limit, 0)) / sum(full_length).",
            "Product span status is measured from tokenizer offsets after right truncation.",
            "Supplier-history buckets use history available before the validation cutoff.",
            "Product source strings longer than 200 chars are counted separately from tokenizer truncation.",
        ],
    }
    write_json(out / "audit.json", report)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "review_samples.jsonl").open("w") as handle:
        for sample in samples:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=256)
    args = parser.parse_args()
    report = audit_cards(args.variants, args.data, args.model, args.revision,
                         args.out, args.batch_size)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
