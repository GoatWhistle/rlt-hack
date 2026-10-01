from dataclasses import replace

import httpx

from src.models.enums import WarningCode
from src.models.search_result import SearchWarning
from src.models.upload import StatusCounts
from src.service.errors import SearchTimeoutError, SearchUnavailableError
from tests.fakes.domain import uid
from tests.fakes.http import FakeServiceProvider
from tests.fakes.uploads import UPLOAD_ID, make_summary, make_upload

DETAIL = f"/api/uploads/{UPLOAD_ID}"
SEARCH = f"/api/searches/{uid('search')}"


async def test_upload_detail_supports_conditional_get(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    first = await client.get(DETAIL)
    tag = first.headers["etag"]
    assert first.headers["cache-control"] == "private, no-cache"
    assert provider.uploads.details == 1
    again = await client.get(DETAIL, headers={"If-None-Match": tag})
    assert again.status_code == 304
    assert again.content == b""
    assert provider.uploads.details == 1
    gzipped = await client.get(DETAIL, headers={"If-None-Match": tag.removeprefix("W/")})
    assert gzipped.status_code == 304


async def test_upload_progress_changes_the_tag(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    tag = (await client.get(DETAIL)).headers["etag"]
    progressed = make_summary(make_upload(total=2), StatusCounts(ready=1, failed=1))
    provider.uploads.detail = replace(provider.uploads.detail, summary=progressed)
    changed = await client.get(DETAIL, headers={"If-None-Match": tag})
    assert changed.status_code == 200
    assert changed.headers["etag"] != tag
    assert changed.json()["processed"] == 2


async def test_upload_summary_is_light_and_cacheable(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    response = await client.get(f"{DETAIL}/summary")
    assert response.status_code == 200
    assert "lots" not in response.json()
    assert provider.uploads.details == 0
    again = await client.get(
        f"{DETAIL}/summary", headers={"If-None-Match": response.headers["etag"]}
    )
    assert again.status_code == 304
    missing = await client.get(f"/api/uploads/{uid('missing')}/summary")
    assert missing.json()["code"] == "upload_not_found"


async def test_saved_search_is_revalidated_by_tag(client: httpx.AsyncClient) -> None:
    first = await client.get(SEARCH)
    assert first.headers["cache-control"] == "private, no-cache"
    again = await client.get(SEARCH, headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304
    assert again.headers["x-request-id"]


async def test_lists_are_not_stored(client: httpx.AsyncClient) -> None:
    for path in ("/api/searches", "/api/uploads"):
        assert (await client.get(path)).headers["cache-control"] == "no-store"


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
