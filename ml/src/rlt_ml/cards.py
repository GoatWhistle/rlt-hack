"""Построение вариантов карточек из нормализованной DuckDB и исходных полей."""

import argparse
import json
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import duckdb
import pyarrow as arrow
import pyarrow.parquet as parquet

from rlt_ml.common import read_config, sha256, sql_string, write_json

CARD_EXAMPLES_SQL = r"""
WITH product_names AS (
    SELECT lot_id, category, left(product_name, 200) product_name,
           min(coalesce(okpd2_code, '')) okpd2_code,
           arg_max(product_name, length(product_name)) source_name,
           max(length(product_name)) source_length
    FROM products
    GROUP BY lot_id, category, left(product_name, 200)
), ranked_products AS (
    SELECT *, row_number() OVER (
        PARTITION BY lot_id, category ORDER BY product_name, okpd2_code
    ) item_rank
    FROM product_names
), product_summary AS (
    SELECT lot_id, category,
           array_to_string(list(product_name ORDER BY product_name), '; ') product_text,
           list(struct_pack(name := product_name, source_name := source_name,
                            source_length := source_length, code := okpd2_code)
                ORDER BY product_name, okpd2_code) product_items
    FROM ranked_products
    WHERE item_rank <= 5
    GROUP BY lot_id, category
), history_descriptions AS (
    SELECT p.supplier_inn, c.category, l.lot_id, l.publish_date,
           left(l.query_text, 400) query_excerpt,
           coalesce(d.product_text, '') product_text,
           left(l.query_text, 400) || ' ' || coalesce(d.product_text, '') profile_description,
           coalesce(d.product_items,
                    []::STRUCT(name VARCHAR, source_name VARCHAR, source_length BIGINT, code VARCHAR)[])
               product_items
    FROM participations p
    JOIN lot_info l USING (lot_id)
    JOIN lot_categories c USING (lot_id)
    LEFT JOIN product_summary d USING (lot_id, category)
    WHERE l.publish_date < {history_before}::DATE AND NOT l.notice_conflict
), descriptions AS (
    SELECT supplier_inn, category, profile_description,
           max(publish_date) last_date,
           count(DISTINCT lot_id) lot_count,
           first(query_excerpt ORDER BY publish_date DESC, query_excerpt, product_text) query_excerpt,
           first(product_items ORDER BY publish_date DESC, query_excerpt, product_text) product_items
    FROM history_descriptions
    GROUP BY supplier_inn, category, profile_description
), selected_examples AS (
    SELECT d.*, row_number() OVER (
        PARTITION BY supplier_inn, category
        ORDER BY last_date DESC, profile_description
    ) example_rank
    FROM descriptions d
)
SELECT e.supplier_inn, e.category, e.profile_description, e.last_date,
       e.query_excerpt, e.product_items, e.example_rank, e.lot_count
FROM selected_examples e
JOIN selected_profiles s USING (supplier_inn, category)
WHERE e.example_rank <= {examples_per_card}
ORDER BY e.supplier_inn, e.category, e.example_rank
"""


def _norm(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def _unique_products(examples: list[dict], limit: int) -> list[dict]:
    rows = [list(example["product_items"] or []) for example in examples]
    selected = []
    seen = set()
    depth = 0
    while len(selected) < limit and any(depth < len(items) for items in rows):
        for items in rows:
            if depth >= len(items):
                continue
            item = items[depth]
            key = _norm(item["name"])
            if key and key not in seen:
                selected.append(item)
                seen.add(key)
                if len(selected) == limit:
                    break
        depth += 1
    return selected


def compact_profile(category: str, examples: list[dict], product_limit: int = 15) -> tuple[str, list[dict]]:
    products = _unique_products(examples, product_limit)
    section = "Категория ОКПД2: " + category + "."
    if products:
        text = "Товары и услуги: " + "; ".join(
            f"{item['name']} (ОКПД2 {item['code']})" if item["code"] else item["name"]
            for item in products
        )
        section += " " + text + "."
    notices = []
    seen_notices = set()
    for example in examples:
        notice = example["query_excerpt"].strip()
        key = _norm(notice)
        if key and key not in seen_notices:
            notices.append(notice)
            seen_notices.add(key)
    if notices:
        section += " Примеры закупок: " + " ; ".join(notices) + "."
    if not products and not notices:
        section += " Недостаточно текстовых примеров."
    return section, products


def subgroup(code: str, digits_count: int = 6) -> str:
    digits = re.sub(r"\D", "", code)
    if len(digits) >= digits_count:
        parts = [digits[:2], digits[2:4]]
        parts.extend(digits[index:index + 2]
                     for index in range(4, digits_count, 2))
        return ".".join(parts)
    if digits:
        return "код " + code
    return "без кода в источнике"


def compact_group_profile(category: str, label: str, examples: list[dict],
                          product_limit: int = 15) -> tuple[str, list[dict]]:
    products = _unique_products(examples, product_limit)
    text = f"Категория ОКПД2: {category}. Группа позиций: {label}."
    if products:
        text += " Товары и услуги: " + "; ".join(
            f"{item['name']} (ОКПД2 {item['code']})" if item["code"] else item["name"]
            for item in products
        ) + "."
    notices, seen = [], set()
    for example in examples:
        notice = example["query_excerpt"].strip()
        key = _norm(notice)
        if key and key not in seen:
            notices.append(notice)
            seen.add(key)
    if notices:
        text += " Примеры закупок: " + " ; ".join(notices) + "."
    return text, products


def _add_mentions(card_id: str, items: list[dict], profile_text: str, preferred_start: int = 0) -> list[dict]:
    mentions = []
    cursor = preferred_start
    for item in items:
        displayed = item["name"]
        start = profile_text.find(displayed, cursor)
        if start < 0:
            start = profile_text.find(displayed)
        if start < 0:
            continue
        end = start + len(displayed)
        source_name = item.get("source_name", displayed)
        mentions.append({
            "card_id": card_id,
            "source_product_name": source_name,
            "displayed_text": displayed,
            "source_char_count": int(item.get("source_length", len(source_name))),
            "displayed_char_count": len(displayed),
            "okpd2_code": item.get("code", ""),
            "start_char": start,
            "end_char": end,
        })
        cursor = end
    return mentions


def _source_examples(base_cards: list[dict], db_path: Path, history_before: str,
                     examples_per_card: int) -> dict[tuple[str, str], list[dict]]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        profile_rows = []
        seen_profiles = set()
        for row in base_cards:
            key = (row["supplier_inn"], row["category"])
            if key not in seen_profiles:
                profile_rows.append({"supplier_inn": key[0], "category": key[1]})
                seen_profiles.add(key)
        selected = arrow.Table.from_pylist(profile_rows)
        con.register("selected_profiles", selected)
        query = CARD_EXAMPLES_SQL.format(
            history_before=sql_string(history_before), examples_per_card=int(examples_per_card)
        )
        rows = con.execute(query).fetch_arrow_table().to_pylist()
    finally:
        con.close()
    result: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        items = row["product_items"] or []
        for item in items:
            item["source_name"] = item["name"]
        result[(row["supplier_inn"], row["category"])].append(row)
    return dict(result)


def _group_examples(examples: list[dict], group_digits: int = 6) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for example in examples:
        items_by_group: dict[str, list[dict]] = defaultdict(list)
        for item in example["product_items"] or []:
            items_by_group[subgroup(item.get("code", ""), group_digits)].append(item)
        if not items_by_group:
            items_by_group["без товарных строк"] = []
        for label, items in items_by_group.items():
            groups[label].append({**example, "product_items": items})
    ranked = []
    for label, rows in groups.items():
        newest = max(row["last_date"] for row in rows)
        ranked.append({
            "label": label,
            "examples": sorted(rows, key=lambda row: (-row["last_date"].toordinal(),
                                                       row["profile_description"])),
            "distinct_lots": sum(int(row["lot_count"]) for row in rows),
            "newest": newest,
        })
    return sorted(ranked, key=lambda row: (-row["distinct_lots"], -row["newest"].toordinal(),
                                           row["label"]))


def _build_c_cards(base_cards: list[dict], examples: dict[tuple[str, str], list[dict]],
                   max_cards_per_supplier: int, product_limit: int = 15,
                   group_digits: int = 6) -> tuple[list[dict], list[dict]]:
    by_supplier: dict[str, list[dict]] = defaultdict(list)
    for card in base_cards:
        by_supplier[card["supplier_inn"]].append(card)
    output, mentions = [], []
    for supplier_inn, category_cards in sorted(by_supplier.items()):
        categories = sorted(
            category_cards,
            key=lambda row: (-float(row.get("participations", 0)),
                             -date.fromisoformat(str(row["profile_last_date"])[:10]).toordinal(),
                             row["category"]),
        )
        groups = []
        for card in categories:
            rows = examples[(supplier_inn, card["category"])]
            groups.append((card, _group_examples(rows, group_digits)))
        selected_groups = []
        depth = 0
        while len(selected_groups) < max_cards_per_supplier and any(depth < len(items) for _, items in groups):
            for card, items in groups:
                if depth < len(items):
                    selected_groups.append((card, items[depth]))
                    if len(selected_groups) == max_cards_per_supplier:
                        break
            depth += 1
        for card, group in selected_groups:
            profile_text, products = compact_group_profile(
                card["category"], group["label"], group["examples"], product_limit
            )
            card_id = f"{supplier_inn}:{card['category']}:{group['label']}"
            output.append({
                **card,
                "card_id": card_id,
                "profile_text": profile_text,
                "example_count": len({row["profile_description"] for row in group["examples"]}),
                "subcategory_group": group["label"],
            })
            prefix = profile_text.find("Товары и услуги: ")
            if prefix >= 0:
                prefix += len("Товары и услуги: ")
                mentions.extend(_add_mentions(card_id, products, profile_text, prefix))
    return sorted(output, key=lambda row: row["card_id"]), mentions


def _build_b_cards(base_cards: list[dict], examples: dict[tuple[str, str], list[dict]],
                   product_limit: int) -> tuple[list[dict], list[dict]]:
    output, mentions = [], []
    for card in base_cards:
        key = (card["supplier_inn"], card["category"])
        rows = examples[key]
        profile_text, products = compact_profile(card["category"], rows, product_limit)
        output.append({**card, "profile_text": profile_text})
        prefix = profile_text.find("Товары и услуги: ")
        if prefix >= 0:
            prefix += len("Товары и услуги: ")
            mentions.extend(_add_mentions(card["card_id"], products, profile_text, prefix))
    return output, mentions


def _baseline_mentions(base_cards: list[dict],
                       examples: dict[tuple[str, str], list[dict]]) -> list[dict]:
    mentions = []
    for card in base_cards:
        key = (card["supplier_inn"], card["category"])
        cursor = 0
        for row in examples[key]:
            line = row["profile_description"]
            line_start = card["profile_text"].find(line, cursor)
            if line_start < 0:
                line_start = card["profile_text"].find(line)
            if line_start < 0:
                continue
            product_start = line_start + len(row["query_excerpt"]) + 1
            mentions.extend(_add_mentions(card["card_id"], row["product_items"],
                                          card["profile_text"], product_start))
            cursor = line_start + len(line) + 1
    return mentions


def build_variants(data: Path, database: Path, out: Path, config_path: Path) -> dict:
    config = read_config(config_path)
    split = config["split"]
    if out.exists():
        raise FileExistsError(f"Выберите новый каталог результатов: {out}")
    base_cards_path = data / split / "cards.parquet"
    base_cards = parquet.read_table(base_cards_path).to_pylist()
    examples = _source_examples(base_cards, database, config["history_before"],
                                int(config["examples_per_card"]))
    for card in base_cards:
        rows = examples.get((card["supplier_inn"], card["category"]), [])
        reconstructed = "\n".join(row["profile_description"] for row in rows)
        if reconstructed != card["profile_text"]:
            raise ValueError(f"Не удалось точно воспроизвести исходную карточку {card['card_id']}")
    base_suppliers = {card["supplier_inn"] for card in base_cards}
    variants = {
        "A": (base_cards, _baseline_mentions(base_cards, examples), "current", 256),
        "B": (*_build_b_cards(base_cards, examples, int(config["compact_product_limit"])),
              "compact", 256),
        "C": (*_build_c_cards(
                  base_cards, examples, int(config["c_max_cards_per_supplier"]),
                  int(config["compact_product_limit"]),
                  int(config["variant_c"]["group_by_okpd2_digits"])),
              "grouped", 256),
        "D": (base_cards, _baseline_mentions(base_cards, examples), "current", 512),
    }
    manifests = {}
    for name, (cards, mentions, representation, card_max_length) in variants.items():
        suppliers = {card["supplier_inn"] for card in cards}
        supplier_counts = Counter(card["supplier_inn"] for card in cards)
        if suppliers != base_suppliers:
            raise ValueError(f"Вариант {name} изменил набор поставщиков")
        folder = out / name
        folder.mkdir(parents=True)
        card_path = folder / "cards.parquet"
        mention_path = folder / "product_mentions.parquet"
        if name in {"A", "D"}:
            shutil.copyfile(base_cards_path, card_path)
        else:
            parquet.write_table(arrow.Table.from_pylist(cards), card_path, compression="zstd")
        parquet.write_table(arrow.Table.from_pylist(mentions), mention_path, compression="zstd")
        manifest = {
            "schema_version": 1,
            "variant": name,
            "representation": representation,
            "card_max_length": card_max_length,
            "query_max_length": int(config["query_max_length"]),
            "examples_per_card": int(config["examples_per_card"]),
            "max_cards_per_supplier": (int(config["c_max_cards_per_supplier"])
                                       if name == "C" else int(config["max_cards_per_supplier"])),
            "compact_product_limit": int(config["compact_product_limit"]),
            "card_count": len(cards),
            "supplier_count": len(suppliers),
            "max_cards_for_one_supplier": max(supplier_counts.values()),
            "product_mention_count": len(mentions),
            "source_manifest_sha256": sha256(data / "manifest.json"),
            "baseline_cards_sha256": sha256(base_cards_path),
            "cards_sha256": sha256(card_path),
            "mentions_sha256": sha256(mention_path),
        }
        write_json(folder / "manifest.json", manifest)
        manifests[name] = manifest
    write_json(out / "manifest.json", {
        "config": config,
        "variants": manifests,
        "invariants": ["same supplier INN set", "same validation queries", "same history cutoff"],
    })
    return manifests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_variants(args.data, args.database, args.out, args.config),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
