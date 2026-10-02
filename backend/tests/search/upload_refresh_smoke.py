import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.repository.uploads.files import FileUploads
from src.models.operations.upload import Notice
from src.models.search.supplier_search import SupplierCandidate
from src.service.upload.worker import UploadService


class Search:
    version = "first"
    calls = 0

    async def search(self, text, limit=10):
        self.calls += 1
        await asyncio.sleep(0)
        return [SupplierCandidate("1111111111", "paper", self.version, 1.0, 1.0)]


async def main():
    with TemporaryDirectory() as temporary:
        repository = FileUploads(Path(temporary))
        search = Search()
        service = UploadService(search, repository)
        owner = "a" * 32
        upload = await service.create(owner, "test.csv", [Notice("lot", "paper")])
        assert not upload.lots[0].processed
        await service.drain()
        assert upload.ranking_version == "first" and search.calls == 1
        await service.get(owner, upload.upload_id)
        assert search.calls == 1
        search.version = "second"
        results = await asyncio.gather(*(service.get(owner, upload.upload_id) for _ in range(5)))
        assert all(item.ranking_version == "first" for item in results)
        await service.drain()
        assert search.calls == 2
        results = await asyncio.gather(*(service.get(owner, upload.upload_id) for _ in range(5)))
        assert all(item.ranking_version == "second" for item in results)
        assert all(item.lots[0].candidates[0].profile == "second" for item in results)
        assert results[0].created_at == upload.created_at
        await service.drain()
        assert await service.get("b" * 32, upload.upload_id) is None
        assert search.calls == 2
        restored = await repository.get(owner, upload.upload_id)
        assert restored.ranking_version == "second"
    print("Upload ranking versions, persistence, isolation and concurrent refresh: OK")


asyncio.run(main())
