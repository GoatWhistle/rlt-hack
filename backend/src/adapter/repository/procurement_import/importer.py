import asyncio
import hashlib
import json
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from src.adapter.repository.procurement_import.columns import COLUMNS, REGISTRY_COLUMNS
from src.adapter.repository.procurement_import.protocols import SqlGateway
from src.adapter.repository.procurement_import.reader import ArchiveReader


async def import_procurements(
    gateway: SqlGateway,
    database: str,
    prepared: Path,
    directory: Path,
    batch_size: int = 1000,
) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", database) or not 1 <= batch_size <= 10000:
        raise ValueError("Invalid database or batch size")
    manifest = json.loads(await asyncio.to_thread((directory / "manifest.json").read_text))
    before = date.fromisoformat(manifest["history_before"])
    index_id = manifest["files"]["card_vectors.npy"]
    if not re.fullmatch(r"[a-f0-9]{64}", index_id):
        raise ValueError("Invalid archive index identity")
    checksum = await asyncio.to_thread(_checksum, prepared)
    registry = await gateway.select(
        f"SELECT index_id, history_before, prepared_sha256, lots, items, participations, status "
        f"FROM {database}.procurement_archive_imports FINAL",
    )
    if registry and (len(registry) != 1 or tuple(registry[0][:3]) != (index_id, before, checksum)):
        raise ValueError("Archive belongs to another snapshot or prepared source")
    counts = await _counts(gateway, database)
    if not registry and any(counts):
        raise ValueError("Existing archive has no import audit; refusing to mix snapshots")
    if registry and registry[0][6] == "completed":
        if counts != tuple(registry[0][3:6]):
            raise ValueError("Completed archive counts differ from audit")
        return {
            "already_present": True,
            "counts": dict(zip(COLUMNS, counts, strict=True)),
            "history_before": before.isoformat(),
            "index_id": index_id,
        }
    with tempfile.TemporaryDirectory(prefix="rlt-procurements-") as temporary:
        reader = await asyncio.to_thread(ArchiveReader, prepared, before, index_id, Path(temporary))
        try:
            expected = await asyncio.to_thread(reader.counts)
            if not expected[0]:
                raise ValueError("Archive snapshot contains no eligible lots")
            await gateway.insert(
                f"{database}.procurement_archive_imports",
                REGISTRY_COLUMNS,
                [(index_id, before, checksum, *expected, "importing")],
            )
            for table, columns in COLUMNS.items():
                await asyncio.to_thread(reader.start, table)
                while rows := await asyncio.to_thread(reader.read, table, batch_size):
                    await gateway.insert(f"{database}.{table}", columns, rows)
            actual = await _counts(gateway, database)
            if actual != expected:
                raise ValueError("Archive import is incomplete or contains foreign rows")
            await gateway.insert(
                f"{database}.procurement_archive_imports",
                REGISTRY_COLUMNS,
                [(index_id, before, checksum, *expected, "completed")],
            )
        finally:
            await asyncio.to_thread(reader.close)
    return {
        "already_present": False,
        "counts": dict(zip(COLUMNS, actual, strict=True)),
        "history_before": before.isoformat(),
        "index_id": index_id,
    }


async def _counts(gateway: SqlGateway, database: str) -> tuple[int, ...]:
    result = []
    for table in COLUMNS:
        rows = await gateway.select(f"SELECT count() FROM {database}.{table}_current")
        result.append(int(rows[0][0]))
    return tuple(result)


def _checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
