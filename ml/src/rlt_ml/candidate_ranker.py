"""Evaluate CatBoost reranking on candidates returned by supplier retrieval."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import time
from pathlib import Path

from rlt_ml.common import FEATURES, revision, sha256, sql_string, write_json


def _load_predictions(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.open() if line.strip()]
    if not rows:
        raise ValueError("Файл retrieval predictions пуст")
    for row in rows:
        if not row.get("candidate_inns"):
            raise ValueError(f"Нет retrieval-кандидатов для lot_id={row.get('lot_id')}")
    if len({row["lot_id"] for row in rows}) != len(rows):
        raise ValueError("В predictions повторяются lot_id")
    return rows


def _feature_frame(data: Path, rows: list[dict]):
    import duckdb
    import pandas as pd

    candidates = pd.DataFrame([
        {"lot_id": row["lot_id"], "supplier_inn": inn, "retrieval_rank": rank}
        for row in rows
        for rank, inn in enumerate(row["candidate_inns"], start=1)
    ])
    candidates["lot_id"] = candidates.lot_id.astype(str)
    candidates["supplier_inn"] = candidates.supplier_inn.astype(str)
    con = duckdb.connect()
    con.register("candidate_rows", candidates)
    root = data / "validation"
    queries = sql_string(root / "queries.parquet")
    suppliers = sql_string(root / "supplier_stats.parquet")
    customers = sql_string(root / "customer_stats.parquet")
    categories = sql_string(root / "category_stats.parquet")
    products = sql_string(root / "products.parquet")
    query = f"""
        WITH lot_categories AS (
            SELECT DISTINCT lot_id, category
            FROM read_parquet({products})
        ), category_features AS (
            SELECT c.lot_id, c.supplier_inn,
                   count(cs.supplier_inn) FILTER (WHERE lc.category != 'unknown')
                       / max(q.category_count)::DOUBLE AS category_coverage,
                   sum(coalesce(cs.participations, 0)) AS category_participations,
                   sum(coalesce(cs.wins, 0)) AS category_wins
            FROM candidate_rows c
            JOIN read_parquet({queries}) q USING (lot_id)
            LEFT JOIN lot_categories lc USING (lot_id)
            LEFT JOIN read_parquet({categories}) cs
              ON cs.supplier_inn = c.supplier_inn AND cs.category = lc.category
            GROUP BY c.lot_id, c.supplier_inn
        )
        SELECT c.lot_id, c.supplier_inn, c.retrieval_rank,
               (s.supplier_inn IS NOT NULL)::INTEGER AS has_history,
               ln(1 + coalesce(s.participations, 0)) AS log_participations,
               (coalesce(s.wins, 0) + 1.0) / (coalesce(s.participations, 0) + 2.0)
                   AS win_rate,
               ln(1 + coalesce(cs.participations, 0)) AS log_customer_participations,
               (coalesce(cs.wins, 0) + 1.0) / (coalesce(cs.participations, 0) + 2.0)
                   AS customer_win_rate,
               coalesce(cf.category_coverage, 0) AS category_coverage,
               ln(1 + coalesce(cf.category_participations, 0))
                   AS log_category_participations,
               (coalesce(cf.category_wins, 0) + 1.0)
                   / (coalesce(cf.category_participations, 0) + 2.0)
                   AS category_win_rate,
               coalesce(abs(ln(1 + q.start_price) - s.mean_log_price), 0)
                   AS price_log_distance,
               coalesce(date_diff('day', s.last_date, q.publish_date), 3650)
                   AS days_since_last,
               ln(1 + coalesce(q.start_price, 0)) AS log_start_price,
               ln(1 + q.product_count) AS log_product_count
        FROM candidate_rows c
        JOIN read_parquet({queries}) q USING (lot_id)
        LEFT JOIN read_parquet({suppliers}) s USING (supplier_inn)
        LEFT JOIN read_parquet({customers}) cs
          ON cs.supplier_inn = c.supplier_inn AND cs.customer_inn = q.customer_inn
        LEFT JOIN category_features cf USING (lot_id, supplier_inn)
        ORDER BY c.lot_id, c.retrieval_rank
    """
    try:
        frame = con.execute(query).df()
    finally:
        con.close()
    if len(frame) != len(candidates):
        raise ValueError("Построение признаков изменило число пар lot—supplier")
    return frame


def _rank_metrics(rows: list[dict], ranked: dict[str, list[str]]) -> dict:
    valid = [row for row in rows if row.get("winner_inn")]
    ranks = []
    for row in valid:
        ordered = ranked[row["lot_id"]]
        winner = row["winner_inn"]
        ranks.append(ordered.index(winner) + 1 if winner in ordered else 0)
    if not ranks:
        return {"lots_with_unique_winner": 0, "winner_recall_in_candidates": None,
                "hit_at_1": None, "hit_at_5": None, "mrr": None}
    present = [rank > 0 for rank in ranks]
    return {
        "lots_with_unique_winner": len(ranks),
        "winner_recall_in_candidates": sum(present) / len(ranks),
        "hit_at_1": sum(rank == 1 for rank in ranks) / len(ranks),
        "hit_at_5": sum(1 <= rank <= 5 for rank in ranks) / len(ranks),
        "mrr": sum(1 / rank if rank else 0 for rank in ranks) / len(ranks),
    }


def evaluate(data: Path, predictions_path: Path, model_path: Path, out: Path) -> dict:
    import catboost

    started = time.monotonic()
    if out.exists():
        raise FileExistsError(f"Выберите новый каталог отчёта: {out}")
    rows = _load_predictions(predictions_path)
    features = _feature_frame(data, rows)
    model = catboost.CatBoostRanker()
    model.load_model(str(model_path))
    features["catboost_score"] = model.predict(features[FEATURES])
    baseline, reranked = {}, {}
    for lot_id, group in features.groupby("lot_id", sort=False):
        baseline[lot_id] = group.sort_values("retrieval_rank").supplier_inn.tolist()
        reranked[lot_id] = group.sort_values(
            ["catboost_score", "supplier_inn"], ascending=[False, True], kind="stable"
        ).supplier_inn.tolist()
    report = {
        "source_git_revision": revision(),
        "input_mode": "retrieval_candidates_and_known_products_features",
        "data_manifest_sha256": sha256(data / "manifest.json"),
        "predictions_sha256": sha256(predictions_path),
        "model_sha256": sha256(model_path),
        "query_sample_sha256": hashlib.sha256(
            json.dumps([row["lot_id"] for row in rows]).encode()
        ).hexdigest(),
        "queries": len(rows),
        "candidate_count": int(len(features)),
        "features": FEATURES,
        "retrieval_order": _rank_metrics(rows, baseline),
        "catboost_reranked": _rank_metrics(rows, reranked),
        "duration_seconds": round(time.monotonic() - started, 2),
        "peak_ram_gib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 2),
        "limitations": [
            "Оценка использует исторические ТРУ и признаки на validation; качества определения ТРУ из извещения здесь нет.",
            "Исторические участники неполно размечают предметную релевантность поставщиков.",
            "CatBoost прогнозирует исторического победителя среди найденного пула, не вероятность и не качество исполнения.",
        ],
    }
    out.mkdir(parents=True)
    write_json(out / "report.json", report)
    with (out / "ranked_candidates.jsonl").open("w") as handle:
        for row in rows:
            lot_id = row["lot_id"]
            handle.write(json.dumps({
                "lot_id": lot_id,
                "retrieval_candidates": baseline[lot_id],
                "catboost_candidates": reranked[lot_id],
                "winner_in_pool": row.get("winner_inn") in baseline[lot_id]
                    if row.get("winner_inn") else None,
            }, ensure_ascii=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.data, args.predictions, args.model, args.out),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
