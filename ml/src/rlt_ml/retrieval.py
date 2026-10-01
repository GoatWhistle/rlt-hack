"""Одинаковая оценка TF–IDF и готовых/дообученных энкодеров по поставщикам."""

import argparse
import ctypes
import hashlib
import json
import resource
import time
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as arrow
import pyarrow.parquet as parquet
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from rlt_ml.common import read_config, revision, sha256, sql_string, write_json


def torch_float32_to_numpy(tensor):
    """Copy CPU float32 tensor data without PyTorch's NumPy C-API bridge.

    Some CUDA images ship a Torch build compiled against NumPy 1 and NumPy 2;
    CUDA inference works there, but ``Tensor.numpy()`` cannot initialize.
    """
    import torch

    value = tensor.detach().to(device="cpu", dtype=torch.float32).contiguous()
    raw = ctypes.string_at(value.data_ptr(), value.numel() * 4)
    return np.frombuffer(raw, dtype=np.float32).reshape(tuple(value.shape))


def lexical_index(texts: list[str], model: str):
    if model == "tfidf":
        vectorizer = TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2), max_features=120000,
            sublinear_tf=True, dtype=np.float32,
        )
        return vectorizer, vectorizer.fit_transform(texts)
    vectorizer = CountVectorizer(lowercase=True, max_features=120000, dtype=np.float32)
    matrix = vectorizer.fit_transform(texts).tocsr()
    lengths = np.asarray(matrix.sum(axis=1)).ravel()
    df = np.asarray((matrix > 0).sum(axis=0)).ravel()
    idf = np.log1p((len(texts) - df + 0.5) / (df + 0.5))
    normalization = 1.2 * (0.25 + 0.75 * lengths / max(float(lengths.mean()), 1))
    row_indices = np.repeat(np.arange(len(texts)), np.diff(matrix.indptr))
    matrix.data = (
        matrix.data * 2.2 / (matrix.data + normalization[row_indices]) * idf[matrix.indices]
    ).astype(np.float32)
    return vectorizer, matrix


def reciprocal_rank_fusion(dense: list[str], lexical: list[str], top_k: int = 100) -> list[str]:
    scores = {}
    for ranking in (dense, lexical):
        for position, inn in enumerate(ranking, start=1):
            scores[inn] = scores.get(inn, 0) + 1 / (60 + position)
    return sorted(scores, key=lambda inn: (-scores[inn], inn))[:top_k]


def unique_suppliers(scores, supplier_inns: list[str], top_k: int, card_cap: int = 8,
                     positive_only: bool = False) -> list[str]:
    """Максимум по карточкам компании; сумма не даёт бонус за число направлений."""
    size = min(len(scores), top_k * card_cap)
    if size == 0:
        return []
    indices = np.argpartition(-scores, size - 1)[:size]
    indices = indices[np.argsort(-scores[indices], kind="stable")]
    result, seen = [], set()
    for index in indices:
        if positive_only and scores[index] <= 0:
            continue
        inn = supplier_inns[index]
        if inn not in seen:
            seen.add(inn)
            result.append(inn)
            if len(result) == top_k:
                break
    return result


def summarize(predictions: list[dict]) -> dict:
    recalls, winners, ranks = [], [], []
    for row in predictions:
        known = set(row["participants"])
        candidates = row["candidate_inns"]
        if known:
            recalls.append(len(known.intersection(candidates)) / len(known))
        if row["winner_inn"]:
            hit = row["winner_inn"] in candidates
            winners.append(hit)
            ranks.append(1 / (candidates.index(row["winner_inn"]) + 1) if hit else 0)
    return {
        "queries": len(predictions), "queries_with_participants": len(recalls),
        "recall_at_100": float(np.mean(recalls)) if recalls else None,
        "winner_recall_at_100": float(np.mean(winners)) if winners else None,
        "winner_mrr_at_100": float(np.mean(ranks)) if ranks else None,
    }


def evaluate(data: Path, out: Path, split: str, model_id: str, config: dict,
             input_mode: str = "notice_text", device: str = "cuda", hybrid: bool = False,
             cards_path: Path | None = None, lexical_cards_path: Path | None = None) -> dict:
    if out.exists():
        raise FileExistsError(f"Выберите новый каталог оценки: {out}")
    if config["top_k"] != 100:
        raise ValueError("В этом отчёте фиксирована метрика @100; top_k должен быть 100")
    folder = data / split
    source_cards = cards_path or folder / "cards.parquet"
    cards = parquet.read_table(source_cards).to_pylist()
    if not cards:
        raise ValueError("История не содержит карточек поставщиков")
    with duckdb.connect() as con:
        query_path = sql_string(folder / "queries.parquet")
        limit = f"LIMIT {int(config['max_queries'])}" if config["max_queries"] else ""
        queries = con.execute(f"""
            SELECT * FROM read_parquet({query_path}) WHERE participant_count > 0
            ORDER BY hash(lot_id, {int(config['seed'])}) {limit}
        """).fetch_arrow_table().to_pylist()
    targets = parquet.read_table(folder / "targets.parquet").to_pylist()
    history_rows = parquet.read_table(folder / "supplier_stats.parquet").to_pylist()
    history_counts = {row["supplier_inn"]: int(row["participations"])
                      for row in history_rows}
    winners = {}
    for row in targets:
        if row["is_winner"] and not row["label_conflict"]:
            winners.setdefault(row["lot_id"], []).append(row["supplier_inn"])
    product_names = {}
    if input_mode == "known_products":
        for row in parquet.read_table(folder / "products.parquet").to_pylist():
            product_names.setdefault(row["lot_id"], []).append(
                row["product_name"] + " " + (row["okpd2_code"] or "")
            )
    texts = [q["query_text"] if input_mode == "notice_text"
             else q["query_text"] + " " + " ; ".join(product_names.get(q["lot_id"], []))
             for q in queries]
    profile_texts = [c["profile_text"] for c in cards]
    inns = [c["supplier_inn"] for c in cards]
    card_cap = max(np.unique(inns, return_counts=True)[1])
    known_inns = set(inns)
    started = time.monotonic()
    base_revision = None
    timings = {}
    runtime = {}
    dense_predictions = None
    out.mkdir(parents=True)
    write_json(out / "status.json", {"stage": "starting", "model": model_id})
    if model_id in {"tfidf", "bm25"}:
        if hybrid:
            raise ValueError("Гибридный поиск требует dense model, а не лексическую базу")
        vectorizer, profiles = lexical_index(profile_texts, model_id)
        query_vectors = vectorizer.transform(texts)
        if model_id == "bm25":
            query_vectors = query_vectors.sign()
        predictions = [unique_suppliers((profiles @ query_vectors[i].T).toarray().ravel(),
                                        inns, 100, int(card_cap), True)
                       for i in range(len(texts))]
    else:
        import torch

        from rlt_ml.text_encoder import TextEncoder

        torch.set_num_threads(int(config.get("cpu_threads", 4)))
        if device == "cuda":
            torch.cuda.set_per_process_memory_fraction(float(config.get("gpu_memory_fraction", 1)))
            torch.cuda.reset_peak_memory_stats()
        model_start = time.monotonic()
        encoder = TextEncoder(
            model_id,
            config["max_length"],
            config["query_instruction"],
            device,
            quantization=config.get("quantization", "none"),
            card_max_length=int(config.get("card_max_length", config["max_length"])),
        )
        encoder.model.eval()
        timings["model_load_seconds"] = round(time.monotonic() - model_start, 2)
        batch_size = config["batch_size"]
        indexing_start = time.monotonic()
        profile_batches = []
        with torch.inference_mode():
            for start in range(0, len(profile_texts), batch_size):
                profile_batches.append(encoder(profile_texts[start:start + batch_size], query=False).cpu())
                if start % (100 * batch_size) == 0:
                    elapsed = time.monotonic() - indexing_start
                    completed = min(start + batch_size, len(profile_texts))
                    print(f"cards={completed}/{len(cards)} elapsed={elapsed:.1f}s", flush=True)
                    write_json(out / "status.json", {
                        "stage": "encoding_cards", "model": model_id,
                        "completed_cards": completed, "total_cards": len(cards),
                        "elapsed_seconds": round(elapsed, 2),
                    })
            profiles = torch.cat(profile_batches)
            del profile_batches
            timings["index_encode_seconds"] = round(time.monotonic() - indexing_start, 2)
            np.save(out / "card_vectors.npy", torch_float32_to_numpy(profiles))
            parquet.write_table(arrow.Table.from_pylist(cards), out / "cards.parquet")
            predictions = []
            query_start = time.monotonic()
            for start in range(0, len(texts), batch_size):
                vectors = encoder(texts[start:start + batch_size], query=True).cpu()
                scores = torch_float32_to_numpy(vectors @ profiles.T)
                predictions.extend(unique_suppliers(s, inns, 300 if hybrid else 100, int(card_cap))
                                   for s in scores)
            timings["query_batch_seconds"] = round(time.monotonic() - query_start, 2)
        base_revision = encoder.base_revision
        dense_predictions = [p[:100] for p in predictions]
        if hybrid:
            lexical_cards = (parquet.read_table(lexical_cards_path).to_pylist()
                             if lexical_cards_path else cards)
            lexical_texts = [c["profile_text"] for c in lexical_cards]
            lexical_inns = [c["supplier_inn"] for c in lexical_cards]
            lexical_cap = max(np.unique(lexical_inns, return_counts=True)[1])
            vectorizer, lexical_profiles = lexical_index(lexical_texts, "bm25")
            lexical_queries = vectorizer.transform(texts).sign()
            predictions = [reciprocal_rank_fusion(
                dense, unique_suppliers((lexical_profiles @ lexical_queries[i].T).toarray().ravel(),
                                        lexical_inns, 300, int(lexical_cap), True))
                for i, dense in enumerate(predictions)]
        latencies = []
        with torch.inference_mode():
            for i, text in enumerate(texts[:32]):
                request_start = time.monotonic()
                vector = encoder([text], query=True).cpu()
                dense = unique_suppliers(torch_float32_to_numpy(vector @ profiles.T).ravel(), inns,
                                         300 if hybrid else 100, int(card_cap))
                if hybrid:
                    lexical = unique_suppliers(
                        (lexical_profiles @ lexical_queries[i].T).toarray().ravel(),
                        lexical_inns, 300, int(lexical_cap), True)
                    reciprocal_rank_fusion(dense, lexical)
                latencies.append(time.monotonic() - request_start)
        if latencies:
            timings["warm_single_query_p50_ms"] = round(float(np.percentile(latencies, 50)) * 1000, 2)
            timings["warm_single_query_p95_ms"] = round(float(np.percentile(latencies, 95)) * 1000, 2)
            timings["latency_queries"] = len(latencies)
        runtime = {"torch": torch.__version__, "torch_cuda": torch.version.cuda}
        if config.get("quantization") == "nf4":
            import bitsandbytes

            runtime["bitsandbytes"] = bitsandbytes.__version__
        if device == "cuda":
            runtime.update({
                "gpu": torch.cuda.get_device_name(),
                "peak_vram_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
                "peak_vram_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 2),
            })
    rows = []
    for row_index, (query, candidates) in enumerate(zip(queries, predictions, strict=True)):
        winner_list = winners.get(query["lot_id"], [])
        winner = winner_list[0] if len(winner_list) == 1 and not query["label_conflict"] else None
        participants = query["known_positive_inns"]
        rows.append({
            "lot_id": query["lot_id"], "candidate_inns": candidates,
            "dense_candidate_inns": (dense_predictions[row_index]
                                      if dense_predictions is not None else None),
            "procedure_group": query.get("procedure_group") or ("lot:" + query["lot_id"]),
            "participants": participants, "winner_inn": winner,
            "has_unseen_supplier": any(inn not in known_inns for inn in participants),
            "has_low_history_supplier": any(1 <= history_counts.get(inn, 0) <= 5
                                            for inn in participants),
            "multiposition": query["product_count"] > 1,
        })
    report = {
        "source_git_revision": revision(), "model": model_id, "base_revision": base_revision,
        "split": split, "config": config, "input_mode": input_mode,
        "hybrid": hybrid,
        "data_manifest_sha256": sha256(data / "manifest.json"),
        "cards_sha256": sha256(source_cards),
        "lexical_cards_sha256": sha256(lexical_cards_path or source_cards) if hybrid else None,
        "query_sample_sha256": hashlib.sha256(
            json.dumps([q["lot_id"] for q in queries]).encode()).hexdigest(),
        "procedure_sample_sha256": hashlib.sha256(
            json.dumps([q.get("procedure_group") for q in queries]).encode()).hexdigest(),
        "all": summarize(rows),
        "with_unseen_supplier": summarize([r for r in rows if r["has_unseen_supplier"]]),
        "with_low_history_supplier": summarize(
            [r for r in rows if r["has_low_history_supplier"]]
        ),
        "multiposition": summarize([r for r in rows if r["multiposition"]]),
        "duration_seconds": round(time.monotonic() - started, 2),
        "card_count": len(cards), "supplier_count": len(known_inns),
        "timings": timings, "runtime": runtime,
        "peak_ram_gib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 2),
        "limitations": [
            "Исторические участники — неполная разметка релевантности.",
            "notice_text оценивает прямой поиск по извещению без отдельного определения ТРУ.",
            "winner_mrr — положение победителя в поиске, без CatBoost и без вероятности победы.",
        ],
    }
    if dense_predictions is not None:
        report["dense_only"] = summarize([
            {**row, "candidate_inns": dense} for row, dense in zip(rows, dense_predictions, strict=True)
        ])
    write_json(out / "report.json", report)
    write_json(out / "status.json", {"stage": "completed", "model": model_id})
    with (out / "predictions.jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split", choices=["validation", "test"], default="validation")
    parser.add_argument("--model", default="bm25", help="tfidf, bm25, HF model id или путь к адаптеру")
    parser.add_argument("--hybrid", action="store_true", help="BM25 + dense с RRF")
    parser.add_argument("--cards", type=Path, help="Parquet карточек для dense индекса")
    parser.add_argument("--lexical-cards", type=Path,
                        help="Зафиксированные карточки BM25 для гибридного поиска")
    parser.add_argument("--config", type=Path, default=Path("ml/configs/retrieval.toml"))
    parser.add_argument("--input-mode", choices=["notice_text", "known_products"], default="notice_text")
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--card-max-length", type=int)
    parser.add_argument("--quantization", choices=["none", "nf4"], default="none")
    parser.add_argument("--gpu-memory-fraction", type=float)
    parser.add_argument("--cpu-threads", type=int)
    args = parser.parse_args()
    config = read_config(args.config)
    if args.batch_size is not None:
        config["batch_size"] = args.batch_size
    if args.card_max_length is not None:
        config["card_max_length"] = args.card_max_length
    if args.gpu_memory_fraction is not None:
        config["gpu_memory_fraction"] = args.gpu_memory_fraction
    if args.cpu_threads is not None:
        config["cpu_threads"] = args.cpu_threads
    config.setdefault("gpu_memory_fraction", 1)
    config.setdefault("cpu_threads", 4)
    config["quantization"] = args.quantization
    if config["batch_size"] < 1 or not 0 < config["gpu_memory_fraction"] <= 1:
        parser.error("batch-size > 0; 0 < gpu-memory-fraction <= 1")
    print(evaluate(args.data, args.out, args.split, args.model,
                   config, args.input_mode, args.device, args.hybrid, args.cards,
                   args.lexical_cards))


if __name__ == "__main__":
    main()
