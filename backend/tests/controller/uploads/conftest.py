from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from src.adapter.repository.uploads.files import FileUploads
from src.controller.search.api import app
from src.models.supplier_search import SupplierCandidate
from src.service.upload.worker import UploadService

CSV = b"lot_id,procedure_name\nL1,paper\n"


class FakeEngine:
    def __init__(self) -> None:
        self.failure: Exception | None = None
        self.calls = 0

    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return [SupplierCandidate("1111111111", "paper", "office paper", 1.0, 0.9)]


@pytest.fixture
def engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def service(engine: FakeEngine, tmp_path: Path) -> UploadService:
    return UploadService(engine, FileUploads(tmp_path))


@pytest.fixture
async def search_client(
    engine: FakeEngine, service: UploadService
) -> AsyncIterator[httpx.AsyncClient]:
    app.state.search = engine
    app.state.uploads = service
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
        yield client


def assert_error(response: httpx.Response, status: int, code: str) -> dict[str, str]:
    assert response.status_code == status, response.text
    body: dict[str, str] = response.json()
    assert body["code"] == code
    assert body["message"]
    assert body["requestId"] == response.headers["X-Request-Id"]
    return body
