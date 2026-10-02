import logging

import httpx
import pytest
from starlette.requests import Request

from src.controller.http.errors import handle_http
from src.models.errors import (
    InvalidCandidateError,
    InvalidProcurementLotError,
    InvalidQueryItemError,
    InvalidScoreError,
)
from src.service.errors import (
    ProviderNotConfiguredError,
    SearchNotFoundError,
    SearchTimeoutError,
    SearchUnavailableError,
    StorageUnavailableError,
    SupplierNotFoundError,
    UninterpretableQueryError,
)
from tests.fakes.domain import uid
from tests.fakes.http import FakeServiceProvider
from tests.fakes.uploads import UPLOAD_ID

SECRET = "password=hunter2 at clickhouse:8123"


def assert_error(response: httpx.Response, status: int, code: str) -> None:
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"code", "message", "requestId"}
    assert body["code"] == code
    assert body["requestId"] == response.headers["x-request-id"]


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"text": "   "}, "empty_query"),
        ({"text": "а" * 4001}, "query_too_long"),
        ({"text": "рис", "limit": 0}, "invalid_limit"),
        ({"text": "рис", "limit": 51}, "invalid_limit"),
        ({"text": "рис", "extra": 1}, "invalid_request"),
        ({"text": "рис", "filters": {"region": "78"}}, "invalid_request"),
        ({"text": "рис", "filters": {"itemType": "food"}}, "invalid_request"),
        ({"text": "рис", "limit": "20"}, "invalid_request"),
        ({"text": 5}, "invalid_request"),
        ({}, "invalid_request"),
    ],
)
async def test_invalid_search_requests(
    client: httpx.AsyncClient, provider: FakeServiceProvider, payload: object, code: str
) -> None:
    response = await client.post("/api/searches", json=payload)
    assert_error(response, 422, code)
    assert provider.searching.queries == []


async def test_malformed_json_is_invalid_request(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/searches", content=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert_error(response, 422, "invalid_request")


async def test_too_long_text_message_matches_contract(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/searches", json={"text": "а" * 4001})
    assert response.json()["message"] == "search text is longer than 4000 characters"


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (UninterpretableQueryError(), 422, "query_not_understood"),
        (SearchNotFoundError("x"), 404, "search_not_found"),
        (SupplierNotFoundError("x"), 404, "supplier_not_found"),
        (SearchUnavailableError(("lexical",)), 503, "search_unavailable"),
        (SearchTimeoutError(8.0), 504, "search_timeout"),
    ],
)
async def test_service_errors_are_mapped(
    client: httpx.AsyncClient,
    provider: FakeServiceProvider,
    error: Exception,
    status: int,
    code: str,
) -> None:
    provider.searching.error = error
    response = await client.post("/api/searches", json={"text": "рис"})
    assert_error(response, status, code)
    assert response.json()["message"] == str(error)


@pytest.mark.parametrize("error", [RuntimeError(SECRET), ProviderNotConfiguredError(SECRET)])
async def test_unexpected_errors_hide_details(
    client: httpx.AsyncClient,
    provider: FakeServiceProvider,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
) -> None:
    provider.searching.error = error
    with caplog.at_level(logging.ERROR):
        response = await client.get(f"/api/searches/{uid('search')}")
    assert_error(response, 500, "internal_error")
    assert response.json()["message"] == "internal error"
    assert SECRET not in response.text
    assert any(record.exc_info for record in caplog.records)


@pytest.mark.parametrize(
    "error",
    [
        InvalidCandidateError("ranks start at 1"),
        InvalidScoreError(1.7),
        InvalidQueryItemError("name is empty"),
        InvalidProcurementLotError("title is empty"),
    ],
)
async def test_server_side_invariant_violation_is_internal(
    client: httpx.AsyncClient,
    provider: FakeServiceProvider,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
) -> None:
    provider.searching.error = error
    with caplog.at_level(logging.INFO):
        response = await client.post("/api/searches", json={"text": "рис"})
    assert_error(response, 500, "internal_error")
    assert str(error) not in response.text
    failures = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert failures
    assert all(record.exc_info for record in failures)
    assert not [record for record in caplog.records if record.getMessage() == "request rejected"]


async def test_unknown_route_is_not_found(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/unknown")
    assert_error(response, 404, "not_found")


async def test_wrong_method_is_not_allowed(client: httpx.AsyncClient) -> None:
    response = await client.delete("/api/searches")
    assert_error(response, 405, "method_not_allowed")
    assert response.headers["allow"]


async def test_non_http_errors_in_http_handler_are_internal() -> None:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": [], "state": {}})
    response = await handle_http(request, RuntimeError(SECRET))
    assert response.status_code == 500
    assert SECRET.encode() not in response.body


STORAGE_ROUTES = [
    ("GET", "/api/searches", None),
    ("GET", f"/api/searches/{uid('search')}", None),
    ("POST", "/api/searches", {"text": "рис"}),
    ("GET", f"/api/suppliers/{uid('supplier')}", None),
    ("GET", "/api/uploads", None),
    ("GET", f"/api/uploads/{UPLOAD_ID}", None),
    ("GET", f"/api/uploads/{UPLOAD_ID}/lots/L1", None),
    ("POST", f"/api/uploads/{UPLOAD_ID}/results", {"lotIds": ["L1"]}),
]


@pytest.mark.parametrize(("method", "path", "payload"), STORAGE_ROUTES)
async def test_storage_outage_maps_to_503(
    client: httpx.AsyncClient,
    provider: FakeServiceProvider,
    caplog: pytest.LogCaptureFixture,
    method: str,
    path: str,
    payload: object,
) -> None:
    outage = StorageUnavailableError()
    provider.searching.error = outage
    provider.profiles.error = outage
    provider.uploads.error = outage
    with caplog.at_level(logging.ERROR):
        response = await client.request(method, path, json=payload)
    assert_error(response, 503, "storage_unavailable")
    assert response.headers["retry-after"] == "5"
    assert not any(record.levelno >= logging.ERROR for record in caplog.records)


async def test_storage_outage_on_upload_maps_to_503(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    provider.uploads.error = StorageUnavailableError()
    response = await client.post(
        "/api/uploads", files={"file": ("a.csv", b"lot_id;procedure_name")}
    )
    assert_error(response, 503, "storage_unavailable")
