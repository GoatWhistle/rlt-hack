import logging
from collections.abc import AsyncIterator
from dataclasses import replace

import httpx
import pytest
from fastapi import FastAPI

from src.controller.http.app import create_app
from src.controller.http.correlation import RequestIdFilter, current_request_id
from src.controller.http.metrics import Metrics
from src.controller.http.settings import ApiSettings
from src.models.enums import CheckReason, WarningCode
from src.models.search import SearchQuery
from src.models.search_result import SearchResult, SearchWarning
from src.service.supplier_search.retrieval.runner import ChannelRunner
from tests.fakes.domain import make_candidate, make_request, make_result, make_supplier
from tests.fakes.http import FakeServiceProvider, FakeSupplierSearching
from tests.fakes.ports import FakeRetriever

TRACE = "trace-0001-abcd"


class ChannelSearching(FakeSupplierSearching):
    async def search(self, query: SearchQuery) -> SearchResult:
        runner = ChannelRunner((FakeRetriever("lexical", fails=True), FakeRetriever("history")))
        await runner.run(make_request(), 3)
        return await super().search(query)


@pytest.fixture
async def strict_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
def correlated(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.handler.addFilter(RequestIdFilter())
    caplog.set_level(logging.INFO)
    return caplog


def fields(record: logging.LogRecord, *names: str) -> tuple[object, ...]:
    return tuple(vars(record)[name] for name in names)


def completed(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.getMessage() == "request completed"]


async def test_unhandled_error_is_logged_once_with_status(
    strict_client: httpx.AsyncClient,
    provider: FakeServiceProvider,
    correlated: pytest.LogCaptureFixture,
) -> None:
    provider.searching.error = RuntimeError("password=hunter2")
    response = await strict_client.post(
        "/api/searches", json={"text": "рис"}, headers={"X-Request-Id": TRACE}
    )
    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "internal error",
        "requestId": TRACE,
    }
    assert response.headers["server-timing"].startswith("app;dur=")
    assert response.headers["x-request-id"] == TRACE
    [record] = completed(correlated)
    assert fields(record, "status", "request_id", "route") == (500, TRACE, "/api/searches")
    errors = [record for record in correlated.records if record.levelno == logging.ERROR]
    assert len(errors) == 1
    assert errors[0].exc_info


async def test_service_logs_carry_the_request_id(correlated: pytest.LogCaptureFixture) -> None:
    provider = FakeServiceProvider(searching=ChannelSearching())
    app = create_app(provider, ApiSettings())
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/searches", json={"text": "рис"}, headers={"X-Request-Id": TRACE}
            )
    assert response.status_code == 201
    [failure] = [record for record in correlated.records if record.levelno == logging.WARNING]
    assert fields(failure, "request_id", "channel") == (TRACE, "lexical")
    assert current_request_id() is None


async def test_search_outcome_is_reported_and_counted(
    app: FastAPI,
    client: httpx.AsyncClient,
    provider: FakeServiceProvider,
    correlated: pytest.LogCaptureFixture,
) -> None:
    unsure = make_candidate(make_supplier("beta"), rank=2, reasons=(CheckReason.INN_MISSING,))
    warning = SearchWarning(WarningCode.CHANNEL_FAILED, "history")
    result = replace(make_result(make_candidate(), unsure), warnings=(warning,))
    provider.searching.result = result
    await client.post("/api/searches", json={"text": "рис"})
    [event] = [record for record in correlated.records if record.getMessage() == "search completed"]
    assert fields(event, "candidates", "recommended", "check", "empty") == (2, 1, 1, False)
    assert fields(event, "warnings") == (["channelFailed:history"],)
    registry: Metrics = app.state.metrics
    assert registry.value("search_candidates_total", {"status": "recommended"}) == 1
    assert registry.value("search_candidates_total", {"status": "check"}) == 1
    labels = {"code": "channelFailed", "subject": "history"}
    assert registry.value("search_warnings_total", labels) == 1
    exposition = (await client.get("/api/metrics")).text
    assert 'search_warnings_total{code="channelFailed",subject="history"} 1' in exposition
    assert "# TYPE http_requests_total counter" in exposition


async def test_empty_search_is_counted(
    app: FastAPI, client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    provider.searching.result = make_result()
    await client.post("/api/searches", json={"text": "рис"})
    registry: Metrics = app.state.metrics
    assert registry.value("search_empty_total") == 1
    assert registry.value("search_requests_total") == 1
