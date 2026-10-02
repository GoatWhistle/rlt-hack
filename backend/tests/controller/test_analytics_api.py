import httpx

from src.models.analytics.filters import AnalyticsFilters
from src.models.analytics.records import RecordProblem
from src.models.enums import SourceType
from src.service.errors import AnalyticsUnavailableError
from tests.fakes.analytics import SOURCE
from tests.fakes.http import FakeServiceProvider


async def test_overview_returns_one_snapshot_with_ratios_and_attention(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/api/analytics/overview")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["meta"]["definitionsVersion"]
    assert body["meta"]["delaySeconds"] == 12
    assert body["offers"] == 10
    assert body["fresh"] == {"numerator": 6, "denominator": 9, "unknown": 1, "share": 6 / 9}
    assert body["attention"][0]["code"] == "source_failed"
    assert [item["code"] for item in body["categories"]] == ["01", ""]
    assert body["categories"][0]["name"] == "Продукция сельского хозяйства"
    assert body["sources"][0]["state"] == "failed"


async def test_filters_reach_the_service_and_invalid_ones_are_rejected(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    ok = await client.get(
        "/api/analytics/quality",
        params={"sourceId": str(SOURCE.source_id), "sourceType": "directory", "region": " 78 "},
    )
    assert ok.status_code == 200
    assert provider.catalog.scopes == [
        AnalyticsFilters(SOURCE.source_id, SourceType.DIRECTORY, "78")
    ]
    assert (
        await client.get("/api/analytics/quality", params={"sourceType": "x"})
    ).status_code == 422
    assert (
        await client.get("/api/analytics/quality", params={"sourceId": "nope"})
    ).status_code == 422


async def test_categories_sources_and_runs_expose_their_parts(client: httpx.AsyncClient) -> None:
    categories = (await client.get("/api/analytics/categories")).json()
    assert categories["origins"][0] == {"key": "system", "count": 6}
    assert categories["items"][1]["parent"] == "01"
    sources = (await client.get("/api/analytics/sources")).json()
    assert sources["items"][0]["lastAttemptStatus"] == "failed"
    runs = (await client.get("/api/analytics/runs")).json()
    assert runs["success"]["share"] == 0.5
    assert runs["items"][0]["errorMessage"] == "boom"
    quality = (await client.get("/api/analytics/quality")).json()
    assert quality["problems"][0]["stale"] == 5


async def test_records_page_is_validated_and_filtered(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    response = await client.get(
        "/api/analytics/records",
        params={"category": "01.11", "problem": "stale", "limit": 5, "offset": 10},
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["okpd2Code"] == "01.11.1"
    query = provider.catalog.queries[0]
    assert (query.category, query.problem, query.limit, query.offset) == (
        "01.11",
        RecordProblem.STALE,
        5,
        10,
    )
    assert (await client.get("/api/analytics/records", params={"limit": 1000})).status_code == 422
    assert (await client.get("/api/analytics/records", params={"problem": "x"})).status_code == 422


async def test_unavailable_snapshot_is_reported_as_retryable(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    provider.catalog.error = AnalyticsUnavailableError("none")
    response = await client.get("/api/analytics/overview")
    assert response.status_code == 503
    assert response.json()["code"] == "analytics_unavailable"
    assert response.headers["retry-after"]
