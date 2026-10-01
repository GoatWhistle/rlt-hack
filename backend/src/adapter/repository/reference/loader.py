"""Чтение файлов справочников: единственное место, где они берутся с диска."""

import asyncio
import json
from pathlib import Path
from typing import Any

from src.adapter.repository.errors import ReferenceDataError


async def read_json(path: Path) -> dict[str, Any]:
    if not await asyncio.to_thread(path.is_file):
        raise ReferenceDataError(f"файл справочника не найден: {path}")
    raw = await asyncio.to_thread(path.read_text, encoding="utf-8")
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ReferenceDataError(f"{path.name}: не разбирается как JSON: {error}") from error
    if not isinstance(document, dict):
        raise ReferenceDataError(f"{path.name}: ожидался объект верхнего уровня")
    return document
