"""Нормализация архива и подготовка временных выборок без загрузки CSV в RAM."""

import argparse
import importlib.metadata
import shutil
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from rlt_ml.common import (
    export,
    read_config,
    revision,
    sha256,
    sql_string,
    validate_splits,
    write_json,
)

SCHEMAS = {
    "notices": {
        "publish_date", "procedure_id", "lot_id", "start_price", "procedure_name", "subject",
        "customer_inn", "is_smp", "is_eshop_or_aisgz",
    },
    "suppliers": {"lot_id", "supplier_inn", "supplier_kpp", "is_winner"},
    "products": {"lot_id", "product_name", "okpd2_code"},
}
ROLE_NAMES = {"извещения": "notices", "поставщики": "suppliers", "тру": "products"}


def source_files(source: Path, raw_dir: Path) -> dict[str, Path]:
    """Извлекает только три ожидаемых CSV; имена членов ZIP не используются как пути."""
    files = {}
    if source.is_dir():
        members = [(p.name, p) for p in sorted(source.glob("*.csv"))]
        archive = None
    else:
        archive = zipfile.ZipFile(source)
        members = [(info.filename, info) for info in archive.infolist() if not info.is_dir()]
    try:
        for name, member in members:
            basename = Path(name).name.lower()
            if not basename.endswith(".csv"):
                continue
            role = next((v for k, v in ROLE_NAMES.items() if basename.startswith(k)), None)
            if role is None:
                continue
            if role in files:
                raise ValueError(f"Повторный CSV для таблицы {role}")
            if archive:
                raw_dir.mkdir(parents=True, exist_ok=True)
                path = raw_dir / f"{role}.csv"
                with archive.open(member) as src, path.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
            else:
                path = member
            with path.open("rb") as handle:
                if handle.read(80).startswith(b"version https://git-lfs.github.com/spec/"):
                    raise ValueError(f"Вместо данных получен указатель Git LFS: {path.name}")
            files[role] = path
    finally:
        if archive:
            archive.close()
    if set(files) != set(SCHEMAS):
        raise ValueError(f"Нужны три CSV: {sorted(SCHEMAS)}; найдены {sorted(files)}")
    return files


def normalize(con, files: dict[str, Path]) -> dict:
    raw_counts = {}
    for role, path in files.items():
        con.execute(f"""
            CREATE TABLE raw_{role} AS SELECT * FROM read_csv(
                {sql_string(path)}, delim=';', header=true, all_varchar=true,
                encoding='utf-8', strict_mode=true, max_line_size=16777216)
        """)
        columns = {row[0].lstrip("\ufeff") for row in con.execute(f"DESCRIBE raw_{role}").fetchall()}
        if not SCHEMAS[role] <= columns:
            raise ValueError(f"Неверная схема {role}: отсутствуют {SCHEMAS[role] - columns}")
        raw_counts[role] = con.execute(f"SELECT count(*) FROM raw_{role}").fetchone()[0]
        print(f"Загружено {role}: {raw_counts[role]:,}", flush=True)

    con.execute(r"""
        CREATE TABLE notices_clean AS
        SELECT trim(lot_id) lot_id, nullif(trim(procedure_id), '') procedure_id,
               try_cast(publish_date AS DATE) publish_date,
               CASE WHEN try_cast(start_price AS DOUBLE) >= 0
                    THEN try_cast(start_price AS DOUBLE) END start_price,
               coalesce(regexp_replace(trim(procedure_name), '\s+', ' ', 'g'), '') procedure_name,
               coalesce(regexp_replace(trim(subject), '\s+', ' ', 'g'), '') subject,
               nullif(trim(customer_inn), '') customer_inn,
               lower(trim(is_smp)) IN ('true', '1', 't') is_smp,
               coalesce(trim(is_eshop_or_aisgz), '') source_system
        FROM raw_notices WHERE nullif(trim(lot_id), '') IS NOT NULL;
        CREATE TABLE notice_versions AS
        SELECT lot_id, count(*) notice_row_count,
               count(DISTINCT hash(procedure_id, publish_date, start_price,
                     procedure_name, subject, customer_inn, is_smp, source_system)) versions
        FROM notices_clean GROUP BY lot_id;
        CREATE TABLE lots AS
        SELECT n.*, v.versions > 1 notice_conflict,
               CASE WHEN n.subject = n.procedure_name THEN n.procedure_name
                    ELSE trim(n.procedure_name || ' ' || n.subject) END query_text
        FROM notices_clean n JOIN notice_versions v USING (lot_id)
        WHERE n.publish_date IS NOT NULL
        QUALIFY row_number() OVER (
            PARTITION BY lot_id ORDER BY publish_date, procedure_name,
            hash(n.procedure_id, n.start_price, n.subject, n.customer_inn, n.source_system)) = 1;
        CREATE TABLE suppliers_clean AS
        SELECT trim(lot_id) lot_id, trim(supplier_inn) supplier_inn,
               try_cast(is_winner AS BOOLEAN) is_winner
        FROM raw_suppliers
        WHERE nullif(trim(lot_id), '') IS NOT NULL
          AND regexp_full_match(trim(supplier_inn), '[0-9]{10}|[0-9]{12}');
        CREATE TABLE participations AS
        SELECT lot_id, supplier_inn, coalesce(bool_or(is_winner), false) is_winner,
               (bool_or(is_winner) AND bool_or(NOT is_winner))
                 OR count(*) FILTER (WHERE is_winner IS NULL) > 0 label_conflict
        FROM suppliers_clean GROUP BY lot_id, supplier_inn;
        CREATE TABLE products AS
        SELECT DISTINCT trim(lot_id) lot_id,
               regexp_replace(trim(product_name), '\s+', ' ', 'g') product_name,
               nullif(trim(okpd2_code), '') okpd2_code,
               coalesce(nullif(regexp_extract(trim(okpd2_code), '^([0-9]{2}\.[0-9]{2})', 1), ''),
                        nullif(regexp_extract(trim(okpd2_code), '^([0-9]{2})', 1), ''),
                        'unknown') category
        FROM raw_products WHERE nullif(trim(lot_id), '') IS NOT NULL
          AND nullif(trim(product_name), '') IS NOT NULL;
        CREATE TABLE lot_categories AS
        SELECT DISTINCT lot_id, category FROM products
        UNION ALL SELECT lot_id, 'unknown' FROM lots
                  WHERE lot_id NOT IN (SELECT lot_id FROM products);
        CREATE TABLE lot_info AS
        WITH prod AS (
            SELECT lot_id, count(*) product_count,
                   list(DISTINCT okpd2_code) FILTER (WHERE okpd2_code IS NOT NULL) okpd2_codes
            FROM products GROUP BY lot_id
        ), part AS (
            SELECT lot_id, count(*) participant_count, sum(is_winner::INTEGER) winner_count,
                   bool_or(label_conflict) label_conflict,
                   list(supplier_inn ORDER BY supplier_inn) known_positive_inns
            FROM participations GROUP BY lot_id
        ), cat AS (
            SELECT lot_id, count(*) category_count FROM lot_categories GROUP BY lot_id
        )
        SELECT l.*, coalesce(prod.product_count, 0) product_count,
               coalesce(prod.okpd2_codes, []::VARCHAR[]) okpd2_codes,
               coalesce(cat.category_count, 1) category_count,
               coalesce(part.participant_count, 0) participant_count,
               coalesce(part.winner_count, 0) winner_count,
               coalesce(part.label_conflict, false) label_conflict,
               coalesce(part.known_positive_inns, []::VARCHAR[]) known_positive_inns
        FROM lots l LEFT JOIN prod USING (lot_id)
        LEFT JOIN part USING (lot_id) LEFT JOIN cat USING (lot_id);
        CREATE TABLE procedure_dates AS
        SELECT coalesce(procedure_id, 'lot:' || lot_id) procedure_group,
               min(publish_date) first_date, max(publish_date) last_date
        FROM lots GROUP BY procedure_group;
    """)
    scalar = lambda query: con.execute(query).fetchone()[0]  # noqa: E731
    quality = {
        "raw_rows": raw_counts,
        "normalized_rows": {t: scalar(f"SELECT count(*) FROM {t}")
                            for t in ("lots", "participations", "products")},
        "supplier_count": scalar("SELECT count(DISTINCT supplier_inn) FROM participations"),
        "invalid_notice_dates": scalar("SELECT count(*) FROM notices_clean WHERE publish_date IS NULL"),
        "notice_conflict_lots": scalar("SELECT count(*) FROM notice_versions WHERE versions > 1"),
        "removed_supplier_rows": raw_counts["suppliers"] - scalar("SELECT count(*) FROM suppliers_clean"),
        "supplier_label_conflicts": scalar("SELECT count(*) FROM participations WHERE label_conflict"),
        "orphan_participations": scalar("SELECT count(*) FROM participations ANTI JOIN lots USING (lot_id)"),
        "orphan_products": scalar("SELECT count(*) FROM products ANTI JOIN lots USING (lot_id)"),
        "single_product_lots": scalar("SELECT count(*) FROM lot_info WHERE product_count = 1"),
        "lots_without_products": scalar("SELECT count(*) FROM lot_info WHERE product_count = 0"),
        "lots_without_winner": scalar("SELECT count(*) FROM lot_info WHERE winner_count = 0"),
        "lots_with_multiple_winners": scalar("SELECT count(*) FROM lot_info WHERE winner_count > 1"),
        "min_date": scalar("SELECT min(publish_date) FROM lots"),
        "max_date": scalar("SELECT max(publish_date) FROM lots"),
    }
    for role in files:
        con.execute(f"DROP TABLE raw_{role}")
    con.execute("DROP TABLE notices_clean; DROP TABLE suppliers_clean")
    return quality


def build_split(con, split: dict, config: dict, root: Path) -> dict:
    name = split["name"]
    before, start, end = (sql_string(split[k]) for k in ("history_before", "start", "end"))
    examples = int(config["examples_per_card"])
    card_limit = int(config["max_cards_per_supplier"])
    pair_limit = int(config["max_pairs_per_supplier"])
    seed = int(config["seed"])
    folder = root / name
    folder.mkdir()
    print(f"Готовится блок {name}: история < {split['history_before']}", flush=True)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE targets AS
        SELECT l.* FROM lot_info l JOIN procedure_dates d
          ON coalesce(l.procedure_id, 'lot:' || l.lot_id) = d.procedure_group
        WHERE l.publish_date >= {start}::DATE AND l.publish_date < {end}::DATE
          AND NOT l.notice_conflict AND d.first_date >= {start}::DATE
          AND d.last_date < {end}::DATE;
        CREATE OR REPLACE TEMP TABLE history AS
        SELECT p.lot_id, p.supplier_inn,
               (p.is_winner AND NOT p.label_conflict AND l.winner_count = 1)::INTEGER winner,
               l.publish_date, l.start_price, l.customer_inn, l.query_text, l.category_count
        FROM participations p JOIN lot_info l USING (lot_id)
        WHERE l.publish_date < {before}::DATE AND NOT l.notice_conflict;
        CREATE OR REPLACE TEMP TABLE supplier_stats AS
        SELECT supplier_inn, count(*) participations, sum(winner) wins,
               avg(ln(1 + start_price)) mean_log_price,
               max(publish_date) last_date
        FROM history GROUP BY supplier_inn;
        CREATE OR REPLACE TEMP TABLE customer_stats AS
        SELECT supplier_inn, customer_inn, count(*) participations, sum(winner) wins
        FROM history WHERE customer_inn IS NOT NULL GROUP BY supplier_inn, customer_inn;
        CREATE OR REPLACE TEMP TABLE category_stats AS
        SELECT supplier_inn, category, count(DISTINCT h.lot_id) distinct_lots,
               sum(1.0 / h.category_count) participations,
               sum(h.winner * 1.0 / h.category_count) wins,
               max(publish_date) last_date
        FROM history h JOIN lot_categories c USING (lot_id) GROUP BY supplier_inn, category;
        CREATE OR REPLACE TEMP TABLE category_descriptions AS
        SELECT lot_id, category,
               array_to_string(list_slice(list(DISTINCT left(product_name, 200)
                                  ORDER BY left(product_name, 200)), 1, 5), '; ') description
        FROM products GROUP BY lot_id, category;
        CREATE OR REPLACE TEMP TABLE descriptions AS
        SELECT h.supplier_inn, c.category,
               left(h.query_text, 400) || ' ' || coalesce(d.description, '') profile_description,
               max(h.publish_date) last_date
        FROM history h JOIN lot_categories c USING (lot_id)
        LEFT JOIN category_descriptions d USING (lot_id, category)
        GROUP BY h.supplier_inn, c.category, profile_description;
        CREATE OR REPLACE TEMP TABLE cards AS
        WITH limited AS (
            SELECT * FROM descriptions
            QUALIFY row_number() OVER (PARTITION BY supplier_inn, category
                                      ORDER BY last_date DESC, profile_description) <= {examples}
        ), text_cards AS (
            SELECT supplier_inn, category,
                   array_to_string(list(profile_description
                                        ORDER BY last_date DESC, profile_description), '\n')
                       profile_text,
                   count(*) example_count, max(last_date) profile_last_date
            FROM limited GROUP BY supplier_inn, category
        )
        SELECT t.*, t.supplier_inn || ':' || t.category card_id, s.participations
        FROM text_cards t JOIN category_stats s USING (supplier_inn, category)
        QUALIFY row_number() OVER (PARTITION BY supplier_inn
                     ORDER BY s.participations DESC, t.profile_last_date DESC, t.category) <= {card_limit};
        CREATE OR REPLACE TEMP TABLE relevant_category_stats AS
        SELECT p.lot_id, p.supplier_inn,
               count(*) FILTER (WHERE cs.supplier_inn IS NOT NULL AND c.category != 'unknown')
                 / max(l.category_count)::DOUBLE category_coverage,
               sum(coalesce(cs.participations, 0)) category_participations,
               sum(coalesce(cs.wins, 0)) category_wins
        FROM participations p JOIN targets l USING (lot_id)
        JOIN lot_categories c USING (lot_id)
        LEFT JOIN category_stats cs USING (supplier_inn, category)
        GROUP BY p.lot_id, p.supplier_inn;
        CREATE OR REPLACE TEMP TABLE ranker_rows AS
        SELECT l.lot_id, p.supplier_inn, p.is_winner::INTEGER AS "label",
               (s.supplier_inn IS NOT NULL)::INTEGER has_history,
               ln(1 + coalesce(s.participations, 0)) log_participations,
               (coalesce(s.wins, 0) + 1.0) / (coalesce(s.participations, 0) + 2.0) win_rate,
               ln(1 + coalesce(cs.participations, 0)) log_customer_participations,
               (coalesce(cs.wins, 0) + 1.0) / (coalesce(cs.participations, 0) + 2.0) customer_win_rate,
               coalesce(rc.category_coverage, 0) category_coverage,
               ln(1 + coalesce(rc.category_participations, 0)) log_category_participations,
               (coalesce(rc.category_wins, 0) + 1.0)
                   / (coalesce(rc.category_participations, 0) + 2.0) category_win_rate,
               coalesce(abs(ln(1 + l.start_price) - s.mean_log_price), 0) price_log_distance,
               coalesce(date_diff('day', s.last_date, l.publish_date), 3650) days_since_last,
               ln(1 + coalesce(l.start_price, 0)) log_start_price,
               ln(1 + l.product_count) log_product_count
        FROM targets l JOIN participations p USING (lot_id)
        LEFT JOIN supplier_stats s USING (supplier_inn)
        LEFT JOIN customer_stats cs USING (supplier_inn, customer_inn)
        LEFT JOIN relevant_category_stats rc USING (lot_id, supplier_inn)
        WHERE l.participant_count > 1 AND l.winner_count = 1 AND NOT l.label_conflict;
        CREATE OR REPLACE TEMP TABLE query_positives AS
        SELECT l.query_text, list(DISTINCT p.supplier_inn ORDER BY p.supplier_inn)
                   known_positive_inns
        FROM targets l JOIN participations p USING (lot_id) GROUP BY l.query_text;
        CREATE OR REPLACE TEMP TABLE encoder_pairs AS
        WITH matched AS (
            SELECT l.lot_id, p.supplier_inn, l.query_text, c.card_id, c.profile_text,
                   qp.known_positive_inns, 1.0 / l.participant_count sample_weight
            FROM targets l JOIN participations p USING (lot_id)
            JOIN lot_categories lc USING (lot_id)
            JOIN cards c ON c.supplier_inn = p.supplier_inn AND c.category = lc.category
            JOIN query_positives qp ON qp.query_text = l.query_text
            WHERE l.product_count = 1 AND length(l.query_text) > 0
            QUALIFY row_number() OVER (PARTITION BY l.lot_id, p.supplier_inn
                                      ORDER BY c.participations DESC, c.card_id) = 1
        )
        SELECT * FROM matched
        {f'QUALIFY row_number() OVER (PARTITION BY supplier_inn ORDER BY hash(lot_id, {seed})) <= {pair_limit}' if name == 'train' else ''};
    """)
    files = {
        "queries": "SELECT * FROM targets ORDER BY publish_date, lot_id",
        "targets": "SELECT p.* FROM participations p JOIN targets l USING (lot_id) ORDER BY lot_id, supplier_inn",
        "products": "SELECT p.* FROM products p JOIN targets l USING (lot_id) ORDER BY lot_id, product_name",
        "cards": "SELECT * FROM cards ORDER BY card_id",
        "supplier_stats": "SELECT * FROM supplier_stats ORDER BY supplier_inn",
        "category_stats": "SELECT * FROM category_stats ORDER BY supplier_inn, category",
        "customer_stats": "SELECT * FROM customer_stats ORDER BY supplier_inn, customer_inn",
        "ranker": "SELECT * FROM ranker_rows ORDER BY lot_id, supplier_inn",
        "encoder_pairs": "SELECT * FROM encoder_pairs ORDER BY lot_id, supplier_inn",
    }
    counts = {key: export(con, sql, folder / f"{key}.parquet") for key, sql in files.items()}
    stats = {
        **split, "rows": counts,
        "history_lots": con.execute("SELECT count(DISTINCT lot_id) FROM history").fetchone()[0],
        "history_max_date": con.execute("SELECT max(publish_date) FROM history").fetchone()[0],
        "eligible_competitive_lots": con.execute("SELECT count(DISTINCT lot_id) FROM ranker_rows").fetchone()[0],
        "unseen_target_participations": con.execute("""
            SELECT count(*) FROM participations p JOIN targets l USING (lot_id)
            ANTI JOIN supplier_stats s USING (supplier_inn)
        """).fetchone()[0],
        "ranker_input_mode": "known_products",
    }
    write_json(folder / "manifest.json", stats)
    print(f"Готов {name}: {counts}", flush=True)
    return stats


def prepare(source: Path, out: Path, config_path: Path) -> dict:
    config = read_config(config_path)
    validate_splits(config)
    source, out = source.resolve(), out.resolve()
    if out.exists():
        raise FileExistsError(f"Результат уже существует; выберите новый каталог: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{out.name}-", dir=out.parent))
    started = time.monotonic()
    con = None
    try:
        files = source_files(source, staging / "raw")
        con = duckdb.connect(str(staging / "procurement.duckdb"))
        con.execute(f"SET threads = {int(config['threads'])}")
        con.execute(f"SET memory_limit = {sql_string(config['memory_limit'])}")
        con.execute(f"SET temp_directory = {sql_string(staging / 'spill')}")
        con.execute("SET preserve_insertion_order = false")
        quality = normalize(con, files)
        splits = [build_split(con, split, config, staging) for split in config["splits"]]
        con.execute("CHECKPOINT")
        con.close()
        con = None
        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "source_git_revision": revision(),
            "config_sha256": sha256(config_path), "config": config,
            "input_sha256": {role: sha256(path) for role, path in files.items()},
            "quality": quality, "splits": splits,
            "duration_seconds": round(time.monotonic() - started, 2),
            "versions": {name: importlib.metadata.version(name)
                         for name in ("duckdb", "pyarrow", "numpy", "catboost", "scikit-learn")},
            "limitations": [
                "Время получения результатов закупок неизвестно; временной тест приближённый.",
                "Ranker-фичи используют настоящие ТРУ и фактических участников; это не полная цепочка.",
                "Encoder-пары ограничены однопозиционными лотами и доступной предшествующей историей.",
                "Queries/targets сохраняют новых поставщиков для общей оценки покрытия.",
                "Непредставленный в лоте поставщик не считается доказанно нерелевантным.",
            ],
        }
        write_json(staging / "manifest.json", manifest)
        shutil.rmtree(staging / "raw", ignore_errors=True)
        shutil.rmtree(staging / "spill", ignore_errors=True)
        staging.rename(out)
        return manifest
    except BaseException:
        if con:
            con.close()
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="ZIP или каталог трёх CSV на сервере")
    parser.add_argument("--out", type=Path, required=True, help="Новый каталог результатов")
    parser.add_argument("--config", type=Path, default=Path("ml/configs/data.toml"))
    args = parser.parse_args()
    manifest = prepare(args.source, args.out, args.config)
    print(f"Готово за {manifest['duration_seconds']} с: {args.out}", flush=True)


if __name__ == "__main__":
    main()
