"""Архивные основания для карточек; подготовленная база открывается только для чтения."""

import asyncio
import hashlib
import json
import tempfile
from datetime import date
from pathlib import Path

import duckdb
import pyarrow.parquet as parquet

from src.adapter.repository.supplier_index.protocols import SqlGateway

COLUMNS = (
    "supplier_inn",
    "category",
    "lot_id",
    "title",
    "publish_date",
    "customer_inn",
    "source_system",
    "product_names",
    "is_winner",
    "category_lots",
    "category_wins",
)


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(database: Path, cards: Path, output: Path, before: date) -> str:
    with database.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    with duckdb.connect(str(database), read_only=True) as connection:
        connection.execute("SET memory_limit='512MB'")
        connection.execute("SET threads=2")
        connection.execute("SET temp_directory=?", [str(output.parent / "spill")])
        connection.execute(
            "CREATE TEMP TABLE selected_cards AS SELECT DISTINCT supplier_inn, category "
            "FROM read_parquet(?)",
            [str(cards)],
        )
        connection.execute(
            """
            CREATE TEMP TABLE evidence AS
            WITH items AS (
                SELECT p.lot_id, p.category,
                       list_slice(list(DISTINCT p.product_name ORDER BY p.product_name), 1, 10)
                           product_names
                FROM products p GROUP BY p.lot_id, p.category
            ), history AS (
                SELECT p.supplier_inn, c.category, l.lot_id,
                       coalesce(nullif(l.procedure_name, ''), l.query_text) title,
                       l.publish_date, coalesce(l.customer_inn, '') customer_inn,
                       l.source_system, coalesce(i.product_names, []) product_names,
                       (p.is_winner AND NOT p.label_conflict AND l.winner_count = 1)
                           ::INTEGER is_winner
                FROM participations p JOIN lot_info l USING (lot_id)
                JOIN lot_categories c USING (lot_id)
                JOIN selected_cards s ON s.supplier_inn=p.supplier_inn AND s.category=c.category
                LEFT JOIN items i ON i.lot_id=l.lot_id AND i.category=c.category
                WHERE l.publish_date < ? AND NOT l.notice_conflict
            )
            SELECT *, count(*) OVER w category_lots, (sum(is_winner) OVER w)::BIGINT category_wins
            FROM history
            WINDOW w AS (PARTITION BY supplier_inn, category)
            QUALIFY row_number() OVER (
                PARTITION BY supplier_inn, category
                ORDER BY is_winner DESC, publish_date DESC, lot_id
            ) <= 5
        """,
            [before],
        )
        connection.execute("COPY evidence TO ? (FORMAT PARQUET)", [str(output)])
    return checksum


async def import_history(
    gateway: SqlGateway,
    database: str,
    prepared: Path,
    directory: Path,
    before: date = date(2024, 12, 1),
) -> dict:
    manifest = json.loads(await asyncio.to_thread((directory / "manifest.json").read_text))
    index_id = manifest["files"]["card_vectors.npy"]
    cards_path = directory / "cards.parquet"
    checksum = await asyncio.to_thread(file_hash, cards_path)
    if checksum != manifest["files"]["cards.parquet"]:
        raise ValueError("Evidence cards checksum mismatch")
    existing = await gateway.select(
        f"SELECT row_count FROM {database}.supplier_evidence_imports FINAL "
        "WHERE index_id={index:String} AND history_before={before:Date}",
        {"index": index_id, "before": before},
    )
    if existing:
        actual = await gateway.select(
            f"SELECT count() FROM {database}.supplier_procurement_evidence FINAL "
            "WHERE index_id={index:String}",
            {"index": index_id},
        )
        if actual != existing:
            raise ValueError("Evidence registry count mismatch")
        return {"rows": existing[0][0], "already_present": True}
    with tempfile.TemporaryDirectory(prefix="rlt-evidence-") as temporary:
        output = Path(temporary) / "evidence.parquet"
        checksum = await asyncio.to_thread(
            prepare, prepared, directory / "cards.parquet", output, before
        )
        source = await asyncio.to_thread(parquet.ParquetFile, output)
        iterator = source.iter_batches(batch_size=500, columns=list(COLUMNS))
        count = 0
        while (batch := await asyncio.to_thread(next, iterator, None)) is not None:
            rows = await asyncio.to_thread(batch.to_pylist)
            await gateway.insert(
                f"{database}.supplier_procurement_evidence",
                ("index_id", *COLUMNS),
                [(index_id, *(row[column] for column in COLUMNS)) for row in rows],
            )
            count += len(rows)
        actual = await gateway.select(
            f"SELECT count() FROM {database}.supplier_procurement_evidence FINAL "
            "WHERE index_id={index:String}",
            {"index": index_id},
        )
        if not count or actual != [(count,)]:
            raise ValueError("Incomplete procurement evidence import")
        await gateway.insert(
            f"{database}.supplier_evidence_imports",
            ("index_id", "history_before", "row_count", "prepared_sha256"),
            [(index_id, before, count, checksum)],
        )
        return {"rows": count, "already_present": False}
