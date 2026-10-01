import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel

from src.controller.http.app import create_app
from src.controller.http.error_body import ApiErrorDto
from src.controller.http.settings import ApiSettings
from src.controller.upload.dto import (
    LotDetailDto,
    LotResultsDto,
    ResultsRequestDto,
    UploadDetailDto,
    UploadListDto,
    UploadSummaryDto,
)
from src.models.errors import (
    MissingNoticeColumnsError,
    NoValidLotsError,
    TooManyNoticeRowsError,
    UnreadableNoticeFileError,
    UnsupportedNoticeFormatError,
)
from src.models.lot_result import LotResult
from src.service.errors import UploadQueueFullError
from tests.controller.test_contracts import key_paths
from tests.fakes.domain import MOMENT, uid
from tests.fakes.http import FakeServiceProvider
from tests.fakes.uploads import UPLOAD_ID, make_lot_detail

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts" / "upload"
CSV = ("notices.csv", "lot_id;procedure_name\n1;Поставка".encode(), "text/csv")


def load(name: str) -> Any:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("name", "model"),
    [
        ("summary.example.json", UploadSummaryDto),
        ("list.example.json", UploadListDto),
        ("detail.example.json", UploadDetailDto),
        ("lot.example.json", LotDetailDto),
        ("results.example.json", LotResultsDto),
        ("results-request.example.json", ResultsRequestDto),
        ("error.example.json", ApiErrorDto),
    ],
)
def test_examples_round_trip_through_dto(name: str, model: type[BaseModel]) -> None:
    example = load(name)
    assert model.model_validate(example).model_dump(by_alias=True, mode="json") == example


async def test_upload_is_accepted_and_located(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    response = await client.post("/api/uploads", files={"file": CSV})
    assert response.status_code == 201
    assert response.headers["Location"] == f"/api/uploads/{UPLOAD_ID}"
    assert key_paths(response.json()) == key_paths(load("summary.example.json"))
    assert provider.uploads.received == [(CSV[0], CSV[1])]


async def test_lists_and_details_match_the_contract(client: httpx.AsyncClient) -> None:
    listed = await client.get("/api/uploads?limit=5")
    assert key_paths(listed.json()) == key_paths(load("list.example.json"))
    detail = (await client.get(f"/api/uploads/{UPLOAD_ID}")).json()
    assert key_paths(detail) == key_paths(load("detail.example.json"))
    assert detail["lots"][0]["status"] == "ready"
    assert detail["issues"] == [{"row": 5, "code": "badPrice", "value": "abc"}]
    lot = (await client.get(f"/api/uploads/{UPLOAD_ID}/lots/4257576")).json()
    assert lot["recommendation"]["products"][0]["origin"] == "notice"
    assert lot["recommendation"]["companies"][0]["checkReasons"] == []
    assert lot["recommendation"]["lotLabel"] == "4257576"


async def test_results_are_returned_for_selected_lots(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    response = await client.post(
        f"/api/uploads/{UPLOAD_ID}/results", json=load("results-request.example.json")
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["recommendation"]["fileName"] == "notices.csv"
    assert provider.uploads.selections == [("4257576", "4633163")]


async def test_queued_and_failed_lots_have_no_recommendation(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    provider.uploads.lot_detail = make_lot_detail(None)
    queued = (await client.get(f"/api/uploads/{UPLOAD_ID}/lots/4257576")).json()
    assert (queued["lot"]["status"], queued["recommendation"]) == ("queued", None)
    provider.uploads.lot_detail = make_lot_detail(LotResult.failure("4257576", MOMENT))
    failed = (await client.get(f"/api/uploads/{UPLOAD_ID}/lots/4257576")).json()
    assert (failed["lot"]["status"], failed["recommendation"]) == ("failed", None)


@pytest.mark.parametrize(
    ("path", "code"),
    [
        (f"/api/uploads/{uid('other')}", "upload_not_found"),
        ("/api/uploads/not-a-uuid", "upload_not_found"),
        (f"/api/uploads/{UPLOAD_ID}/lots/missing", "lot_not_found"),
    ],
)
async def test_missing_resources_are_404(client: httpx.AsyncClient, path: str, code: str) -> None:
    response = await client.get(path)
    assert (response.status_code, response.json()["code"]) == (404, code)


@pytest.mark.parametrize(
    ("kwargs", "status", "code"),
    [
        ({"data": {"other": "x"}}, 400, "missing_file"),
        (
            {"files": {"file": ("notices.xlsx", b"PK", "application/zip")}},
            415,
            "unsupported_file_type",
        ),
        ({"files": {"file": ("notices.csv", b"x" * 2048, "text/csv")}}, 413, "file_too_large"),
    ],
)
async def test_transport_problems_have_stable_codes(
    small_client: httpx.AsyncClient, kwargs: dict[str, Any], status: int, code: str
) -> None:
    response = await small_client.post("/api/uploads", **kwargs)
    assert (response.status_code, response.json()["code"]) == (status, code)


async def test_declared_oversized_body_is_refused_before_parsing(
    small_client: httpx.AsyncClient,
) -> None:
    body = b"x" * (2048 + 70 * 1024)
    response = await small_client.post(
        "/api/uploads", content=body, headers={"Content-Type": "multipart/form-data; boundary=x"}
    )
    assert (response.status_code, response.json()["code"]) == (413, "file_too_large")


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (UnsupportedNoticeFormatError(), 415, "unsupported_file_type"),
        (UnreadableNoticeFileError("empty"), 422, "invalid_file"),
        (MissingNoticeColumnsError(("lot_id",)), 422, "missing_columns"),
        (TooManyNoticeRowsError(5000), 422, "too_many_rows"),
        (NoValidLotsError(), 422, "no_valid_lots"),
    ],
)
async def test_file_problems_have_stable_codes(
    client: httpx.AsyncClient,
    provider: FakeServiceProvider,
    error: Exception,
    status: int,
    code: str,
) -> None:
    provider.uploads.error = error
    response = await client.post("/api/uploads", files={"file": CSV})
    assert (response.status_code, response.json()["code"]) == (status, code)
    assert key_paths(response.json()) == key_paths(load("error.example.json"))


async def test_results_body_is_validated(client: httpx.AsyncClient) -> None:
    response = await client.post(f"/api/uploads/{UPLOAD_ID}/results", json={"lotIds": "1"})
    assert (response.status_code, response.json()["code"]) == (422, "invalid_request")


@pytest.fixture
def small_app(provider: FakeServiceProvider) -> FastAPI:
    return create_app(provider, ApiSettings(upload_max_bytes=1024))


@pytest.fixture
async def small_client(small_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with small_app.router.lifespan_context(small_app):
        transport = httpx.ASGITransport(app=small_app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def test_queue_full_maps_to_429(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    provider.uploads.error = UploadQueueFullError(10000)
    response = await client.post("/api/uploads", files={"file": CSV})
    assert (response.status_code, response.json()["code"]) == (429, "upload_queue_full")
    assert response.headers["retry-after"] == "60"
