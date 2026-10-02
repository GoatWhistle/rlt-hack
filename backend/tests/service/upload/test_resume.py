from src.models.operations.upload import LotRecommendation, Notice, Upload
from src.models.search.supplier_search import SupplierCandidate
from src.service.upload.worker import UploadService
from tests.service.upload.test_worker import OWNER, GatedSearch, MemoryUploads, VersionedSearch


async def test_get_resumes_unprocessed_lots_after_restart() -> None:
    repository = MemoryUploads()
    done = LotRecommendation(Notice("L0", "paper 0"), [SupplierCandidate("2", "x", "kept", 1, 1)])
    stored = Upload(
        "b" * 32,
        OWNER,
        "a.csv",
        "2026-10-02",
        [done, LotRecommendation(Notice("L1", "paper 1"), processed=False)],
        "v1",
    )
    await repository.save(stored)
    search = VersionedSearch("v1")
    service = UploadService(search, repository)
    first = await service.get(OWNER, stored.upload_id)
    second = await service.get(OWNER, stored.upload_id)
    assert first == stored
    assert second == stored
    await search.started.wait()
    search.gate.set()
    await service.drain()
    resumed = await repository.get(OWNER, stored.upload_id)
    assert resumed is not None
    assert search.calls == ["paper 1"]
    assert resumed.lots[0] == done
    assert resumed.lots[1].processed
    assert resumed.lots[1].candidates[0].profile == "paper 1"


async def test_list_resumes_unprocessed_uploads() -> None:
    repository = MemoryUploads()
    stored = Upload(
        "b" * 32,
        OWNER,
        "a.csv",
        "2026-10-02",
        [LotRecommendation(Notice("L0", "paper 0"), processed=False)],
    )
    await repository.save(stored)
    search = GatedSearch()
    search.gate.set()
    service = UploadService(search, repository)
    assert await service.list(OWNER) == [stored]
    await service.drain()
    resumed = await repository.get(OWNER, stored.upload_id)
    assert resumed is not None
    assert resumed.lots[0].processed


async def test_resume_with_a_new_ranking_version_recomputes_every_lot() -> None:
    repository = MemoryUploads()
    stored = Upload(
        "b" * 32,
        OWNER,
        "a.csv",
        "2026-10-02",
        [
            LotRecommendation(Notice("L0", "paper 0")),
            LotRecommendation(Notice("L1", "paper 1"), processed=False),
        ],
        "old",
    )
    await repository.save(stored)
    search = VersionedSearch("new")
    service = UploadService(search, repository)
    assert await service.get(OWNER, stored.upload_id) == stored
    search.gate.set()
    await service.drain()
    resumed = await repository.get(OWNER, stored.upload_id)
    assert resumed is not None
    assert resumed.ranking_version == "new"
    assert sorted(search.calls) == ["paper 0", "paper 1"]


async def test_list_does_not_refresh_finished_uploads() -> None:
    repository = MemoryUploads()
    stored = Upload(
        "b" * 32, OWNER, "a.csv", "2026-10-02", [LotRecommendation(Notice("L0", "paper"))], "old"
    )
    await repository.save(stored)
    search = VersionedSearch("new")
    search.gate.set()
    service = UploadService(search, repository)
    assert await service.list(OWNER) == [stored]
    await service.drain()
    assert search.calls == []
    assert await repository.get(OWNER, stored.upload_id) == stored
