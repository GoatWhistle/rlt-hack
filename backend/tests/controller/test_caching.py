from dataclasses import replace

import httpx

from src.models.enums import WarningCode
from src.models.search_result import SearchWarning
from src.service.errors import SearchTimeoutError, SearchUnavailableError
from tests.fakes.domain import uid
from tests.fakes.http import FakeServiceProvider

SEARCH = f"/api/searches/{uid('search')}"


async def test_saved_search_is_revalidated_by_tag(client: httpx.AsyncClient) -> None:
    first = await client.get(SEARCH)
    assert first.headers["cache-control"] == "private, no-cache"
    again = await client.get(SEARCH, headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304
    assert again.headers["x-request-id"]


async def test_unarchived_search_has_no_location(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    warning = SearchWarning(WarningCode.ARCHIVE_FAILED)
    provider.searching.result = replace(provider.searching.result, warnings=(warning,))
    response = await client.post("/api/searches", json={"text": "рис"})
    assert response.status_code == 200
    assert "location" not in response.headers


async def test_search_outages_ask_to_retry(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    for error in (SearchUnavailableError(("lexical",)), SearchTimeoutError(8.0)):
        provider.searching.error = error
        response = await client.post("/api/searches", json={"text": "рис"})
        assert response.headers["retry-after"] == "5"


async def test_liveness_answers_head(client: httpx.AsyncClient) -> None:
    response = await client.head("/api/health/live")
    assert response.status_code == 200
    assert response.content == b""


async def test_lists_are_not_stored(client: httpx.AsyncClient) -> None:
    for path in ("/api/searches",):
        assert (await client.get(path)).headers["cache-control"] == "no-store"
