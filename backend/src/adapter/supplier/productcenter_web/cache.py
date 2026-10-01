"""Временный дисковый кеш успешных страниц для возобновления обхода."""

import asyncio
import gzip
import hashlib
import os
import time
import zlib
from pathlib import Path
from uuid import uuid4


class PageCache:
    def __init__(self, directory: Path, ttl_seconds: int = 172800) -> None:
        self.directory = directory
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.writes = 0

    def _path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode()).hexdigest()
        return self.directory / digest[:2] / f"{digest}.gz"

    async def read(self, url: str) -> bytes | None:
        path = self._path(url)
        try:
            payload = await asyncio.to_thread(self._read, path, self.ttl_seconds)
        except (OSError, EOFError, zlib.error):
            return None
        if payload is not None:
            self.hits += 1
        return payload

    async def write(self, url: str, content: bytes) -> None:
        path = self._path(url)
        await asyncio.to_thread(self._write, path, content)
        self.writes += 1

    async def invalidate(self, url: str) -> None:
        await asyncio.to_thread(self._path(url).unlink, missing_ok=True)

    @staticmethod
    def _read(path: Path, ttl_seconds: int) -> bytes | None:
        if time.time() - path.stat().st_mtime > ttl_seconds:
            path.unlink(missing_ok=True)
            return None
        return gzip.decompress(path.read_bytes())

    @staticmethod
    def _write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_bytes(gzip.compress(content, compresslevel=3))
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
