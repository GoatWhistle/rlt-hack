import asyncio

import pytest

from src.models.errors import NoValidLotsError
from src.models.operations.upload import Notice, Upload
from src.models.search.supplier_search import SupplierCandidate
from src.service.errors import UploadQueueFullError
from src.service.upload.worker import DEFAULT_MAX_BACKLOG, UploadService

OWNER = "a" * 32


class GatedSearch:
    def __init__(self) -> None:
        self.gate = asyncio.Event()
        self.started = asyncio.Event()
        self.failure: Exception | None = None
        self.failing: set[str] = set()
        self.calls: list[str] = []

    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
        self.started.set()
        self.calls.append(text)
        await self.gate.wait()
        if self.failure is not None:
            raise self.failure
        if text in self.failing:
            raise RuntimeError("search is down")
        return [SupplierCandidate("1111111111", "paper", text, 1.0, 1.0)]


class VersionedSearch(GatedSearch):
    def __init__(self, version: str) -> None:
        super().__init__()
        self.version = version


class MemoryUploads:
    def __init__(self) -> None:
        self.saved: dict[str, Upload] = {}
        self.history: list[Upload] = []

    async def save(self, upload: Upload) -> None:
        self.saved[upload.upload_id] = upload
        self.history.append(upload)

    async def get(self, owner: str, upload_id: str) -> Upload | None:
        return self.saved.get(upload_id)

    async def list(self, owner: str) -> list[Upload]:
        return list(self.saved.values())


def notices(count: int) -> list[Notice]:
    return [Notice(f"L{index}", f"paper {index}") for index in range(count)]


async def finished(service: UploadService, repository: MemoryUploads, upload: Upload) -> Upload:
    await service.drain()
    stored = await repository.get(OWNER, upload.upload_id)
    assert stored is not None
    return stored


def test_backlog_chunk_and_delays_are_validated() -> None:
    with pytest.raises(ValueError, match="0"):
        UploadService(GatedSearch(), MemoryUploads(), 0)
    with pytest.raises(ValueError, match="0"):
        UploadService(GatedSearch(), MemoryUploads(), 10, chunk_lots=0)
    with pytest.raises(ValueError, match="-1"):
        UploadService(GatedSearch(), MemoryUploads(), retry_delays=(-1.0,))


async def test_transient_chunk_failure_is_retried() -> None:
    class FlakySearch(GatedSearch):
        async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
            if len(self.calls) < 2:
                self.calls.append(text)
                raise RuntimeError("inference is warming up")
            return await super().search(text, limit)

    search = FlakySearch()
    search.gate.set()
    repository = MemoryUploads()
    service = UploadService(search, repository, retry_delays=(0.0, 0.0))
    upload = await service.create(OWNER, "a.csv", notices(1))
    stored = await finished(service, repository, upload)
    assert search.calls == ["paper 0", "paper 0", "paper 0"]
    assert stored.lots[0].processed
    assert not stored.lots[0].failed
    assert stored.lots[0].candidates


def test_default_backlog_fits_a_large_file() -> None:
    assert DEFAULT_MAX_BACKLOG >= 5000


async def test_empty_upload_is_rejected() -> None:
    repository = MemoryUploads()
    service = UploadService(GatedSearch(), repository)
    with pytest.raises(NoValidLotsError):
        await service.create(OWNER, "a.csv", [])
    assert repository.saved == {}


async def test_create_returns_queued_lots_before_search_finishes() -> None:
    search = GatedSearch()
    repository = MemoryUploads()
    service = UploadService(search, repository)
    upload = await service.create(OWNER, "a.csv", notices(3))
    assert [lot.processed for lot in upload.lots] == [False, False, False]
    assert all(not lot.candidates for lot in upload.lots)
    assert repository.history == [upload]
    search.gate.set()
    stored = await finished(service, repository, upload)
    assert [lot.processed for lot in stored.lots] == [True, True, True]
    assert [lot.candidates[0].profile for lot in stored.lots] == [
        "paper 0",
        "paper 1",
        "paper 2",
    ]
    assert (stored.created_at, stored.filename) == (upload.created_at, upload.filename)


async def test_progress_is_saved_after_every_chunk() -> None:
    search = VersionedSearch("v1")
    search.gate.set()
    repository = MemoryUploads()
    service = UploadService(search, repository, chunk_lots=2)
    upload = await service.create(OWNER, "a.csv", notices(5))
    await finished(service, repository, upload)
    progress = [sum(lot.processed for lot in item.lots) for item in repository.history]
    assert progress == [0, 2, 4, 5]
    assert repository.history[-1].ranking_version == "v1"


async def test_failed_chunk_marks_its_lots_and_processing_continues() -> None:
    search = GatedSearch()
    search.failing = {"paper 1"}
    search.gate.set()
    repository = MemoryUploads()
    service = UploadService(search, repository, chunk_lots=2, retry_delays=(0.0, 0.0))
    upload = await service.create(OWNER, "a.csv", notices(5))
    stored = await finished(service, repository, upload)
    assert search.calls.count("paper 1") == 3
    assert [lot.failed for lot in stored.lots] == [True, True, False, False, False]
    assert all(lot.processed for lot in stored.lots)
    assert [len(lot.candidates) for lot in stored.lots] == [0, 0, 1, 1, 1]


async def test_storage_failure_stops_processing_without_escaping() -> None:
    class BrokenAfterCreate(MemoryUploads):
        async def save(self, upload: Upload) -> None:
            if any(lot.processed for lot in upload.lots):
                raise OSError("disk is full")
            await super().save(upload)

    search = GatedSearch()
    search.gate.set()
    repository = BrokenAfterCreate()
    service = UploadService(search, repository, 5)
    upload = await service.create(OWNER, "a.csv", notices(5))
    stored = await finished(service, repository, upload)
    assert not any(lot.processed for lot in stored.lots)
    assert len((await service.create(OWNER, "b.csv", notices(5))).lots) == 5
    await service.drain()


async def test_failed_creation_releases_its_reservation() -> None:
    class BrokenUploads(MemoryUploads):
        async def save(self, upload: Upload) -> None:
            raise OSError("disk is full")

    service = UploadService(GatedSearch(), BrokenUploads(), 5)
    with pytest.raises(OSError, match="disk"):
        await service.create(OWNER, "a.csv", notices(5))
    with pytest.raises(OSError, match="disk"):
        await service.create(OWNER, "b.csv", notices(5))


async def test_rejects_upload_when_backlog_is_full() -> None:
    search = GatedSearch()
    repository = MemoryUploads()
    service = UploadService(search, repository, 25)
    running = await service.create(OWNER, "a.csv", notices(20))
    with pytest.raises(UploadQueueFullError) as raised:
        await service.create(OWNER, "b.csv", notices(6))
    assert raised.value.limit == 25
    assert len(repository.saved) == 1
    search.gate.set()
    stored = await finished(service, repository, running)
    assert all(lot.processed for lot in stored.lots)
    assert len((await service.create(OWNER, "b.csv", notices(20))).lots) == 20
    await service.drain()


async def test_failed_upload_releases_its_backlog() -> None:
    search = GatedSearch()
    search.failure = RuntimeError("encoder is down")
    search.gate.set()
    repository = MemoryUploads()
    service = UploadService(search, repository, 20, retry_delays=())
    upload = await service.create(OWNER, "a.csv", notices(20))
    stored = await finished(service, repository, upload)
    assert all(lot.failed for lot in stored.lots)
    search.failure = None
    assert len((await service.create(OWNER, "a.csv", notices(20))).lots) == 20
    await service.drain()


async def test_large_file_is_accepted_when_no_other_upload_is_running() -> None:
    search = GatedSearch()
    search.gate.set()
    service = UploadService(search, MemoryUploads(), 40)
    assert len((await service.create(OWNER, "large.csv", notices(50))).lots) == 50
    with pytest.raises(UploadQueueFullError):
        await service.create(OWNER, "next.csv", notices(1))
    await service.drain()
