import httpx
import pytest

from src.controller.search.api import app
from src.models.operations.upload import Notice, Upload
from src.service.errors import StorageUnavailableError
from tests.controller.uploads.conftest import CSV, FakeEngine, assert_error

UPLOAD = "a" * 32


class UnavailableUploads:
    async def create(self, owner: str, filename: str, notices: list[Notice]) -> Upload:
        raise StorageUnavailableError

    async def get(self, owner: str, upload_id: str) -> Upload | None:
        raise StorageUnavailableError

    async def list(self, owner: str) -> list[Upload]:
        raise StorageUnavailableError


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/uploads", None),
        ("GET", f"/api/uploads/{UPLOAD}", None),
        ("GET", f"/api/uploads/{UPLOAD}/lots/L1", None),
        ("POST", f"/api/uploads/{UPLOAD}/results", {"lotIds": ["L1"]}),
        ("GET", f"/api/uploads/{UPLOAD}/lots/L1/evidence/1111111111/P1", None),
    ],
)
async def test_storage_outage_on_upload_reads_is_503(
    search_client: httpx.AsyncClient, method: str, path: str, body: object
) -> None:
    app.state.uploads = UnavailableUploads()
    response = await search_client.request(method, path, json=body)
    assert_error(response, 503, "storage_unavailable")
    assert response.headers["Retry-After"] == "5"


async def test_storage_outage_while_uploading_is_503(search_client: httpx.AsyncClient) -> None:
    app.state.uploads = UnavailableUploads()
    response = await search_client.post("/api/uploads", files={"file": ("a.csv", CSV)})
    assert_error(response, 503, "storage_unavailable")
    assert response.headers["Retry-After"] == "5"


async def test_storage_outage_during_lot_search_is_503(
    search_client: httpx.AsyncClient, engine: FakeEngine
) -> None:
    engine.failure = StorageUnavailableError()
    uploaded = await search_client.post("/api/uploads", files={"file": ("a.csv", CSV)})
    assert uploaded.status_code == 200, uploaded.text
    searched = await search_client.post("/api/suppliers/search", json={"query": "paper"})
    assert_error(searched, 503, "storage_unavailable")
    assert searched.headers["Retry-After"] == "5"
