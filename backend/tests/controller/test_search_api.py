from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import httpx
import pytest

from src.models.enums import ItemType, Locale
from src.models.ranking.scoring import Score
from src.models.search.query_item import Quantity, QueryItem
from src.models.search.search import CandidateLimit, SearchFilters, SearchQuery, SearchText
from src.models.search.search_result import PipelineInfo, SearchResult, SearchSummary
from tests.fakes.domain import MOMENT, make_candidate, make_item, make_supplier, uid
from tests.fakes.http import FakeServiceProvider

SEARCH_ID = str(uid("search"))


async def test_create_search_returns_created_result(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    response = await client.post(
        "/api/searches",
        json={"text": "  крупа   гречневая ", "limit": 5, "filters": {"regions": ["78", "78"]}},
    )
    assert response.status_code == 201
    assert response.headers["location"] == f"/api/searches/{SEARCH_ID}"
    body = response.json()
    assert body["searchId"] == SEARCH_ID
    assert body["candidates"][0]["contacts"] == {
        "site": "https://alpha.example.org",
        "email": "sales@alpha.example.org",
        "phone": "+7 812 000-00-00",
    }
    query = provider.searching.queries[0]
    assert query.text == SearchText("крупа гречневая")
    assert query.limit == CandidateLimit(5)
    assert query.filters == SearchFilters(regions=("78",))
    assert query.locale == Locale.RU


async def test_create_search_uses_defaults_and_filters(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    response = await client.post(
        "/api/searches",
        json={"text": "рис", "filters": {"itemType": "service"}},
        headers={"Accept-Language": "en-US,en;q=0.9,ru;q=0.5"},
    )
    assert response.status_code == 201
    query = provider.searching.queries[0]
    assert query.limit == CandidateLimit.default()
    assert query.filters.item_type == ItemType.SERVICE
    assert query.locale == Locale.EN


async def test_response_formats_values(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    moscow = timezone(timedelta(hours=3))
    supplier = make_supplier("beta", inn=None)
    item = QueryItem(item_id="i1", name="Рис", quantity=Quantity(Decimal("2E+2"), "кг"))
    provider.searching.result = SearchResult(
        search_id=uid("search"),
        query=SearchQuery(
            text=SearchText("рис"),
            filters=SearchFilters(regions=("78",), item_type=ItemType.GOODS),
        ),
        items=(item, QueryItem(item_id="i2", name="Гречка")),
        candidates=(make_candidate(supplier),),
        pipeline=PipelineInfo("search-v1", ("lexical",), datetime(2026, 10, 1, 15, tzinfo=moscow)),
        created_at=MOMENT.replace(microsecond=0),
    )
    body = (await client.get(f"/api/searches/{SEARCH_ID.upper()}")).json()
    assert body["items"][0]["quantity"] == {"value": "200", "unit": "кг"}
    assert body["items"][1]["quantity"] is None
    assert body["items"][1]["itemType"] == "unknown"
    assert body["pipeline"]["asOf"] == "2026-10-01T12:00:00Z"
    assert body["query"]["filters"] == {"regions": ["78"], "itemType": "goods"}
    assert body["candidates"][0]["inn"] == ""
    assert body["candidates"][0]["id"] == str(supplier.supplier_id)
    assert body["candidates"][0]["score"]["total"] == 0.8


async def test_unknown_item_type_filter_is_reported_as_absent(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    provider.searching.result = SearchResult(
        search_id=uid("search"),
        query=SearchQuery(
            text=SearchText("рис"), filters=SearchFilters(item_type=ItemType.UNKNOWN)
        ),
        items=(make_item(),),
        candidates=(),
        pipeline=PipelineInfo("search-v1", (), MOMENT),
        created_at=MOMENT,
    )
    body = (await client.get(f"/api/searches/{SEARCH_ID}")).json()
    assert body["query"]["filters"]["itemType"] is None
    assert body["candidates"] == []


async def test_scores_are_rounded(client: httpx.AsyncClient, provider: FakeServiceProvider) -> None:
    candidate = make_candidate()
    score = replace(candidate.score, fusion=Score(0.123456), total=Score(0.987654321), channels=())
    result = provider.searching.result
    provider.searching.result = replace(result, candidates=(replace(candidate, score=score),))
    body = (await client.get(f"/api/searches/{SEARCH_ID}")).json()
    assert body["candidates"][0]["score"]["fusion"] == 0.1235
    assert body["candidates"][0]["score"]["total"] == 0.9877
    assert body["candidates"][0]["score"]["channels"] == []


async def test_get_unknown_search_is_not_found(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/searches/{uid('other')}")
    assert response.status_code == 404
    assert response.json()["code"] == "search_not_found"


@pytest.mark.parametrize("search_id", ["not-a-uuid", "123", "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz"])
async def test_get_with_invalid_id_is_not_found(client: httpx.AsyncClient, search_id: str) -> None:
    response = await client.get(f"/api/searches/{search_id}")
    assert response.status_code == 404
    assert response.json()["code"] == "search_not_found"


async def test_recent_uses_default_limit(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    provider.searching.summaries = (
        SearchSummary(
            search_id=uid("search"),
            text=SearchText("рис"),
            locale=Locale.EN,
            items=1,
            candidates=2,
            recommended=1,
            created_at=datetime(2026, 10, 1, 12, 0, 0, 500000, tzinfo=UTC),
        ),
    )
    response = await client.get("/api/searches")
    assert response.status_code == 200
    assert provider.searching.limits == [10]
    assert response.json() == {
        "searches": [
            {
                "searchId": SEARCH_ID,
                "text": "рис",
                "locale": "en",
                "items": 1,
                "candidates": 2,
                "recommended": 1,
                "createdAt": "2026-10-01T12:00:00.500000Z",
            }
        ],
        "hasMore": False,
        "total": 1,
    }
    assert provider.searching.cursors == [None]


async def test_recent_pages_after_a_cursor(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    provider.searching.summaries = tuple(
        SearchSummary(
            search_id=uid(f"search-{index}"),
            text=SearchText("рис"),
            locale=Locale.RU,
            items=1,
            candidates=1,
            recommended=0,
            created_at=datetime(2026, 10, 1, 12, index, tzinfo=UTC),
        )
        for index in range(3)
    )
    response = await client.get("/api/searches", params={"limit": 2, "before": SEARCH_ID})
    body = response.json()
    assert response.status_code == 200
    assert provider.searching.cursors == [UUID(SEARCH_ID)]
    assert len(body["searches"]) == 2
    assert body["hasMore"] is True
    assert body["total"] == 3


async def test_recent_rejects_a_malformed_cursor(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/searches", params={"before": "nope"})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


@pytest.mark.parametrize(("limit", "status"), [(1, 200), (50, 200), (0, 422), (51, 422)])
async def test_recent_limit_bounds(
    client: httpx.AsyncClient, provider: FakeServiceProvider, limit: int, status: int
) -> None:
    response = await client.get("/api/searches", params={"limit": limit})
    assert response.status_code == status
    if status == 422:
        assert response.json()["code"] == "invalid_request"
    else:
        assert provider.searching.limits == [limit]


async def test_ranks_are_passed_through(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    candidates = tuple(
        make_candidate(make_supplier(name), rank=rank)
        for rank, name in enumerate(("alpha", "beta", "gamma"), start=1)
    )
    provider.searching.result = replace(provider.searching.result, candidates=candidates)
    body = (await client.post("/api/searches", json={"text": "рис"})).json()
    assert [candidate["rank"] for candidate in body["candidates"]] == [1, 2, 3]
    assert [candidate["name"] for candidate in body["candidates"]] == [
        "ООО «alpha»",
        "ООО «beta»",
        "ООО «gamma»",
    ]
