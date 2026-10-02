import re

import httpx

from src.controller.http.app import create_app
from src.controller.http.middleware.timing import (
    ServerTimingStages,
    bind_stages,
    release_stages,
    server_timing,
)
from src.controller.http.settings import ApiSettings
from src.models.search.search import SearchQuery
from src.models.search.search_result import SearchResult
from tests.fakes.http import FakeServiceProvider, FakeSupplierSearching

STAGED = re.compile(r"^app;dur=\d+\.\d, parse;dur=\d+\.\d, channels;dur=\d+\.\d$")


class StagedSearching(FakeSupplierSearching):
    async def search(self, query: SearchQuery) -> SearchResult:
        stages = ServerTimingStages()
        with stages.stage("parse"):
            pass
        with stages.stage("channels"):
            pass
        return await super().search(query)


def test_stages_outside_a_request_are_ignored() -> None:
    with ServerTimingStages().stage("parse"):
        pass
    assert server_timing(1.25) == "app;dur=1.2"


def test_stages_are_listed_after_app_time() -> None:
    token = bind_stages()
    try:
        with ServerTimingStages().stage("archive"):
            pass
        assert re.fullmatch(r"app;dur=5\.0, archive;dur=\d+\.\d", server_timing(5.0))
    finally:
        release_stages(token)
    assert server_timing(5.0) == "app;dur=5.0"


async def test_search_response_reports_stages() -> None:
    app = create_app(FakeServiceProvider(searching=StagedSearching()), ApiSettings())
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/searches", json={"text": "рис"})
            health = await client.get("/api/health/live")
    assert response.status_code == 201
    assert STAGED.match(response.headers["server-timing"])
    assert re.fullmatch(r"app;dur=\d+\.\d", health.headers["server-timing"])
