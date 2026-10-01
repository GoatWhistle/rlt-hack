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
    checksum = file_hash(database)
    writer = None
    try:
        with duckdb.connect(str(database), read_only=True) as connection:
            connection.execute("SET memory_limit='1GB'")
            connection.execute("SET threads=1")
            connection.execute("SET preserve_insertion_order=false")
            connection.execute("SET temp_directory=?", [str(output.parent / "spill")])
            connection.execute(
                "CREATE TEMP TABLE selected_cards AS SELECT DISTINCT supplier_inn, category "
                "FROM read_parquet(?)",
                [str(cards)],
            )
            for partition in range(32):
                for table_name in (
                    "chunk_picks",
                    "chunk_lots",
                    "chunk_participations",
                    "chunk_cards",
                ):
                    connection.execute(f"DROP TABLE IF EXISTS {table_name}")
                connection.execute(
                    "CREATE TEMP TABLE chunk_cards AS SELECT * FROM selected_cards "
                    "WHERE hash(supplier_inn) % 32 = ?",
                    [partition],
                )
                connection.execute("""
                    CREATE TEMP TABLE chunk_participations AS
                    SELECT p.lot_id, p.supplier_inn, p.is_winner, p.label_conflict
                    FROM participations p SEMI JOIN chunk_cards s USING (supplier_inn)
                """)
                connection.execute(
                    """
                    CREATE TEMP TABLE chunk_lots AS
                    SELECT l.lot_id, l.publish_date, l.winner_count, l.procedure_name,
                           l.query_text, l.customer_inn, l.source_system
                    FROM lot_info l SEMI JOIN chunk_participations p USING (lot_id)
                    WHERE l.publish_date < ? AND NOT l.notice_conflict
                """,
                    [before],
                )
                connection.execute(
                    """
                    CREATE TEMP TABLE chunk_picks AS
                    WITH history AS (
                        SELECT p.supplier_inn, c.category, l.lot_id, l.publish_date,
                               (p.is_winner AND NOT p.label_conflict AND l.winner_count=1)
                                   ::INTEGER is_winner
                        FROM chunk_participations p JOIN chunk_lots l USING (lot_id)
                        JOIN lot_categories c USING (lot_id)
                        JOIN chunk_cards s
                          ON s.supplier_inn=p.supplier_inn AND s.category=c.category
                    )
                    SELECT *, count(*) OVER w category_lots,
                           (sum(is_winner) OVER w)::BIGINT category_wins
                    FROM history WINDOW w AS (PARTITION BY supplier_inn, category)
                    QUALIFY row_number() OVER (
                        PARTITION BY supplier_inn, category
                        ORDER BY is_winner DESC, publish_date DESC, lot_id
                    ) <= 5
                """,
                )
                table = connection.execute("""
                    SELECT e.supplier_inn, e.category, e.lot_id,
                           coalesce(nullif(l.procedure_name, ''), l.query_text) title,
                           e.publish_date, coalesce(l.customer_inn, '') customer_inn,
                           l.source_system,
                           coalesce(list_slice(list(DISTINCT p.product_name
                               ORDER BY p.product_name) FILTER (WHERE p.product_name IS NOT NULL),
                               1, 10), []) product_names,
                           e.is_winner, e.category_lots, e.category_wins
                    FROM chunk_picks e JOIN chunk_lots l USING (lot_id)
                    LEFT JOIN products p ON p.lot_id=e.lot_id AND p.category=e.category
                    GROUP BY ALL
                """).to_arrow_table()
                if writer is None:
                    writer = parquet.ParquetWriter(output, table.schema, compression="zstd")
                writer.write_table(table)
                print(f"Evidence partition {partition + 1}/32: {table.num_rows} rows", flush=True)
    finally:
        if writer is not None:
            writer.close()
    return checksum


async def import_history(
    gateway: SqlGateway,
    database: str,
    prepared: Path,
    directory: Path,
    before: date | None = None,
) -> dict:
    manifest = json.loads(await asyncio.to_thread((directory / "manifest.json").read_text))
    snapshot = date.fromisoformat(manifest.get("history_before", "2024-12-01"))
    if before is not None and before != snapshot:
        raise ValueError("Evidence cutoff differs from the index snapshot")
    before = snapshot
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
