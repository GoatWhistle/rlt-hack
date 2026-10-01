"""Конфигурация, контроль воспроизводимости и экспорт результатов."""

import hashlib
import json
import subprocess
import tomllib
from datetime import date
from pathlib import Path

FEATURES = [
    "has_history",
    "log_participations",
    "win_rate",
    "log_customer_participations",
    "customer_win_rate",
    "category_coverage",
    "log_category_participations",
    "category_win_rate",
    "price_log_distance",
    "days_since_last",
    "log_start_price",
    "log_product_count",
]


def read_config(path: Path) -> dict:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    return config


def validate_splits(config: dict) -> None:
    names = set()
    previous_end = None
    for split in config["splits"]:
        name = split["name"]
        if name not in {"train", "validation", "test"} or name in names:
            raise ValueError(f"Неизвестное или повторное имя блока: {name}")
        names.add(name)
        history, start, end = (
            date.fromisoformat(split[key]) for key in ("history_before", "start", "end")
        )
        if (start - history).days < 30 or start >= end:
            raise ValueError(f"Неверные границы или зазор менее 30 дней: {name}")
        if previous_end and start < previous_end:
            raise ValueError("Целевые блоки пересекаются")
        previous_end = end
    if names != {"train", "validation", "test"}:
        raise ValueError("Нужны блоки train, validation и test")
    for key in ("examples_per_card", "max_cards_per_supplier", "max_pairs_per_supplier", "threads"):
        if config[key] < 1:
            raise ValueError(f"{key} должен быть положительным")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def revision() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n")


def sql_string(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def export(con, query: str, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY ({query}) TO {sql_string(path)} (FORMAT PARQUET, COMPRESSION ZSTD)")
    return con.execute(f"SELECT count(*) FROM read_parquet({sql_string(path)})").fetchone()[0]
