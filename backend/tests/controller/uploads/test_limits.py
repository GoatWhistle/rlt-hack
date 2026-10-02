import asyncio

import httpx
import pytest

from src.controller.errors import SearchBusyError
from src.controller.search import api
from src.controller.search.admission import Admission
from src.models.operations.upload import Notice, Upload
from src.models.search.supplier_search import SupplierCandidate
from src.service.errors import UploadQueueFullError
from tests.controller.uploads.conftest import CSV, assert_error


class FullUploads:
    async def create(self, owner: str, filename: str, notices: list[Notice]) -> Upload:
        raise UploadQueueFullError(40)

    async def get(self, owner: str, upload_id: str) -> Upload | None:
        return None

    async def list(self, owner: str) -> list[Upload]:
        return []


class SlowEngine:
    def __init__(self) -> None:
        self.gate = asyncio.Event()
        self.started = asyncio.Event()

    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
        self.started.set()
        await self.gate.wait()
        return []


async def test_full_upload_queue_is_429(search_client: httpx.AsyncClient) -> None:
    api.app.state.uploads = FullUploads()
    response = await search_client.post("/api/uploads", files={"file": ("a.csv", CSV)})
    assert_error(response, 429, "upload_queue_full")
    assert response.headers["Retry-After"] == "60"


async def test_supplier_search_beyond_the_limit_is_busy(
    search_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = SlowEngine()
    api.app.state.search = engine
    monkeypatch.setattr(api, "searches", Admission(1))
    running = asyncio.create_task(
        search_client.post("/api/suppliers/search", json={"query": "paper"})
    )
    await engine.started.wait()
    busy = await search_client.post("/api/suppliers/search", json={"query": "cable"})
    assert_error(busy, 503, "search_busy")
    assert busy.headers["Retry-After"] == "5"
    engine.gate.set()
    assert (await running).status_code == 200
    assert api.searches.active == 0


def test_admission_requires_a_positive_limit() -> None:
    with pytest.raises(ValueError, match="0"):
        Admission(0)


def test_admission_releases_a_slot_after_failure() -> None:
    admission = Admission(1)
    with pytest.raises(RuntimeError), admission.slot():
        raise RuntimeError
    with admission.slot(), pytest.raises(SearchBusyError), admission.slot():
        pass
    assert admission.active == 0
