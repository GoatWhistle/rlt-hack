"""CatBoost Ranker на группах фактических участников с временной валидацией."""

import argparse
from pathlib import Path

import duckdb
import numpy as np
from catboost import CatBoostRanker, Pool

from rlt_ml.common import FEATURES, revision, sql_string, write_json


def ranking_metrics(lot_ids, labels, scores) -> dict:
    ranks = []
    groups = {}
    for lot, label, score in zip(lot_ids, labels, scores, strict=True):
        groups.setdefault(lot, []).append((float(score), int(label)))
    for rows in groups.values():
        ordered = sorted(rows, key=lambda row: row[0], reverse=True)
        if sum(label for _, label in ordered) != 1:
            raise ValueError("Метрики единственного победителя требуют ровно одну метку победы")
        ranks.append(next(i + 1 for i, (_, label) in enumerate(ordered) if label))
    values = np.asarray(ranks, dtype=np.float64)
    return {
        "lots": len(ranks),
        "hit_at_1": float(np.mean(values <= 1)) if ranks else None,
        "hit_at_5": float(np.mean(values <= 5)) if ranks else None,
        "mrr": float(np.mean(1 / values)) if ranks else None,
    }


def load_rows(path: Path, max_lots: int = 0, seed: int = 42):
    with duckdb.connect() as con:
        source = f"read_parquet({sql_string(path)})"
        subset = ""
        if max_lots:
            subset = f"""WHERE lot_id IN (
                SELECT DISTINCT lot_id FROM {source}
                ORDER BY hash(lot_id, {int(seed)}) LIMIT {int(max_lots)})"""
        return con.execute(f"SELECT * FROM {source} {subset} ORDER BY lot_id, supplier_inn").df()


def train(data: Path, out: Path, iterations: int, max_lots: int, evaluate_test: bool = False):
    if out.exists():
        raise FileExistsError(f"Выберите новый каталог модели: {out}")
    train_rows = load_rows(data / "train/ranker.parquet", max_lots)
    validation = load_rows(data / "validation/ranker.parquet")
    if train_rows.empty or validation.empty:
        raise ValueError("Для обучения и валидации нужны конкурентные лоты")
    train_pool = Pool(train_rows[FEATURES], train_rows.label, group_id=train_rows.lot_id)
    validation_pool = Pool(validation[FEATURES], validation.label, group_id=validation.lot_id)
    model = CatBoostRanker(
        iterations=iterations, depth=6, learning_rate=0.05,
        loss_function="YetiRank", eval_metric="NDCG:top=5",
        random_seed=42, thread_count=2, allow_writing_files=False,
    )
    model.fit(train_pool, eval_set=validation_pool, early_stopping_rounds=40, verbose=50)
    out.mkdir(parents=True)
    model.save_model(str(out / "ranker.cbm"))
    report = {
        "source_git_revision": revision(), "train_rows": len(train_rows),
        "train_lots": int(train_rows.lot_id.nunique()), "trees": model.tree_count_,
        "features": FEATURES, "input_mode": "known_products_and_actual_participants",
        "validation": {
            "catboost": ranking_metrics(validation.lot_id, validation.label, model.predict(validation_pool)),
            "win_rate_baseline": ranking_metrics(validation.lot_id, validation.label, validation.win_rate),
        },
        "limitations": [
            "Оценка среди фактических участников при известных ТРУ, не полная цепочка поиска.",
            "Балл не является вероятностью победы или оценкой качества поставщика.",
            "Итоговый test запускается отдельно после выбора конфигурации.",
        ],
    }
    if evaluate_test:
        test = load_rows(data / "test/ranker.parquet")
        report["test"] = ranking_metrics(test.lot_id, test.label, model.predict(test[FEATURES]))
    write_json(out / "report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--max-train-lots", type=int, default=50000)
    parser.add_argument("--evaluate-test", action="store_true")
    args = parser.parse_args()
    if args.iterations < 1 or args.max_train_lots < 0:
        parser.error("iterations > 0; max-train-lots >= 0")
    report = train(args.data, args.out, args.iterations, args.max_train_lots, args.evaluate_test)
    print(report)


if __name__ == "__main__":
    main()
