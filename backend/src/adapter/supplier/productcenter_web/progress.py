"""Подтверждённый прогресс обхода; запись после сохранения порции в БД."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4


class CrawlProgress:
    def __init__(self, directory: Path | None) -> None:
        self.path = directory / "crawl-progress.json" if directory else None
        self.started_at: datetime | None = None
        self.products: set[str] = set()
        self.producers: set[str] = set()
        self.listings: dict[str, dict] = {}

    async def resume(self, started_at: datetime) -> datetime:
        if self.path and await asyncio.to_thread(self.path.exists):
            payload = json.loads(await asyncio.to_thread(self.path.read_text))
            if payload["version"] != 1:
                raise ValueError("Unsupported parser checkpoint")
            self.started_at = datetime.fromisoformat(payload["started_at"])
            self.products = set(payload["products"])
            self.producers = set(payload["producers"])
            self.listings = payload["listings"]
        else:
            self.started_at = started_at
        await self.save()
        return self.started_at

    async def save(self) -> None:
        if self.path is None or self.started_at is None:
            return
        payload = json.dumps(
            {
                "version": 1,
                "started_at": self.started_at.isoformat(),
                "products": sorted(self.products),
                "producers": sorted(self.producers),
                "listings": self.listings,
            }
        )
        await asyncio.to_thread(self._write, self.path, payload)

    async def complete(self) -> None:
        if self.path:
            await asyncio.to_thread(self.path.unlink, missing_ok=True)
        self.started_at = None
        self.products.clear()
        self.producers.clear()
        self.listings.clear()

    @staticmethod
    def _write(path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        try:
            with temporary.open("w") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
