import asyncio

import pytest

from src.models.errors import NoValidLotsError, TooManyNoticeRowsError
from src.models.supplier_search import SupplierCandidate
from src.models.upload import Notice, Upload
from src.service.errors import UploadQueueFullError
from src.service.upload.worker import MAX_LOTS, UploadService

OWNER = "a" * 32


class GatedSearch:
    def __init__(self) -> None:
        self.gate = asyncio.Event()
        self.started = asyncio.Event()
        self.failure: Exception | None = None

    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
        self.started.set()
        await self.gate.wait()
        if self.failure is not None:
            raise self.failure
        return [SupplierCandidate("1111111111", "paper", text, 1.0, 1.0)]


class MemoryUploads:
    def __init__(self) -> None:
        self.saved: dict[str, Upload] = {}

    async def save(self, upload: Upload) -> None:
        self.saved[upload.upload_id] = upload

    async def get(self, owner: str, upload_id: str) -> Upload | None:
        return self.saved.get(upload_id)

    async def list(self, owner: str) -> list[Upload]:
        return list(self.saved.values())


def notices(count: int) -> list[Notice]:
    return [Notice(f"L{index}", "paper") for index in range(count)]


def test_backlog_must_fit_a_full_upload() -> None:
    with pytest.raises(ValueError, match=str(MAX_LOTS - 1)):
        UploadService(GatedSearch(), MemoryUploads(), MAX_LOTS - 1)


async def test_file_size_is_checked_with_domain_errors() -> None:
    service = UploadService(GatedSearch(), MemoryUploads())
    with pytest.raises(NoValidLotsError):
        await service.create(OWNER, "a.csv", [])
    with pytest.raises(TooManyNoticeRowsError):
        await service.create(OWNER, "a.csv", notices(MAX_LOTS + 1))


async def test_rejects_upload_when_backlog_is_full() -> None:
    search = GatedSearch()
    service = UploadService(search, MemoryUploads(), MAX_LOTS + 5)
    running = asyncio.create_task(service.create(OWNER, "a.csv", notices(MAX_LOTS)))
    await search.started.wait()
    with pytest.raises(UploadQueueFullError) as raised:
        await service.create(OWNER, "b.csv", notices(6))
    assert raised.value.limit == MAX_LOTS + 5
    search.gate.set()
    upload = await running
    assert len(upload.lots) == MAX_LOTS
    assert len((await service.create(OWNER, "b.csv", notices(MAX_LOTS))).lots) == MAX_LOTS


async def test_failed_upload_releases_its_backlog() -> None:
    search = GatedSearch()
    search.failure = RuntimeError("encoder is down")
    search.gate.set()
    service = UploadService(search, MemoryUploads(), MAX_LOTS)
    with pytest.raises(RuntimeError):
        await service.create(OWNER, "a.csv", notices(MAX_LOTS))
    search.failure = None
    assert len((await service.create(OWNER, "a.csv", notices(MAX_LOTS))).lots) == MAX_LOTS
