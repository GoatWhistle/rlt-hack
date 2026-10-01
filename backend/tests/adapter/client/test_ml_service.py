import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import httpx
import pytest

from src.adapter.client.errors import MlProtocolError, MlServiceError, MlServiceUnavailableError
from src.adapter.client.ml_service.retriever import MlServiceRetriever, utc_now
from src.models.enums import ItemOrigin
from src.models.query_item import QueryItem, SearchRequest
from src.models.retrieval import ItemHit
from src.models.search import SearchFilters, SearchQuery, SearchText
from tests.fakes.domain import MOMENT, make_item, make_request, uid

REQUEST_ID = uid("request")
ALPHA = uid("alpha")
BETA = uid("beta")

type Handler = Callable[[httpx.Request], httpx.Response]


@dataclass(slots=True)
class FakeIdentity:
    known: Mapping[str, UUID] = field(
        default_factory=lambda: {"7801234564": ALPHA, "7807654325": BETA}
    )
    asked: list[tuple[str, ...]] = field(default_factory=list)

    async def ids_by_inn(self, inns: Sequence[str]) -> Mapping[str, UUID]:
        self.asked.append(tuple(inns))
        return {inn: self.known[inn] for inn in inns if inn in self.known}


def answer(candidates: list[dict[str, object]], **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "schemaVersion": "1.0",
        "requestId": str(REQUEST_ID),
        "pipeline": {"pipelineVersion": "supplier-retrieval-v1", "warnings": []},
        "items": [],
        "candidates": candidates,
    }
    body.update(overrides)
    return body


def retriever(handler: Handler, identity: FakeIdentity | None = None) -> MlServiceRetriever:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://ml.local")
    return MlServiceRetriever(
        client,
        identity or FakeIdentity(),
        timeout_seconds=1.0,
        request_ids=lambda: REQUEST_ID,
        clock=lambda: MOMENT,
    )


RANKED = [
    {"supplierInn": "7807654325", "rank": 2, "matchedItemIds": ["i2", "zz"]},
    {"supplierInn": "7801234564", "rank": 1, "matchedItemIds": ["i1", "i1"]},
    {"supplierInn": "0000000000", "rank": 3},
    {"supplierInn": "7801234564", "rank": 4},
]


def regional_request() -> SearchRequest:
    query = SearchQuery(SearchText("крупа"), filters=SearchFilters(regions=("78",)))
    return make_request(make_item("i1"), make_item("i2", "Рис"), query=query)


async def test_candidates_are_mapped_by_inn_in_rank_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/recommendations"
        return httpx.Response(200, json=answer(RANKED))

    hits = await retriever(handler).retrieve(regional_request(), 10)
    assert hits.channel == "semantic"
    assert [(hit.supplier_id, hit.rank) for hit in hits.hits] == [(ALPHA, 1), (BETA, 2)]
    assert hits.hits[0].items == (ItemHit("i1", 1.0),)
    assert hits.hits[1].items == (ItemHit("i2", 0.5),)


async def test_request_follows_the_wire_contract() -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=answer([]))

    await retriever(handler).retrieve(regional_request(), 10)
    body = seen[0]
    assert (body["schemaVersion"], body["requestId"]) == ("1.0", str(REQUEST_ID))
    assert body["asOf"] == "2026-10-01T12:00:00Z"
    assert body["notice"] == {
        "lotId": None,
        "procedureName": "крупа",
        "subject": "",
        "publishedAt": None,
        "startPrice": None,
        "currency": "",
        "customerInn": None,
        "isSmp": None,
        "region": "78",
    }
    item = body["items"][0]
    assert item["quantity"] == "500"
    assert (item["unit"], item["origin"], item["itemType"]) == ("кг", "notice", "goods")
    assert body["options"] == {"candidateLimit": 10, "includeHistoricalEvidence": True}


async def test_limit_cuts_resolved_candidates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        candidates = [
            {"supplierInn": "7801234564", "rank": 1},
            {"supplierInn": "7807654325", "rank": 2},
        ]
        return httpx.Response(200, json=answer(candidates))

    hits = await retriever(handler).retrieve(make_request(), 1)
    assert [hit.supplier_id for hit in hits.hits] == [ALPHA]


@pytest.mark.parametrize(
    "body",
    [
        answer([], requestId=str(uid("other"))),
        answer([], schemaVersion="2.0"),
        answer([{"supplierInn": "7801234564", "rank": 0}]),
        {"unexpected": True},
    ],
)
async def test_protocol_violations_are_errors(body: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    with pytest.raises(MlProtocolError):
        await retriever(handler).retrieve(make_request(), 5)


async def test_transient_failures_are_retried_once() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(200, json=answer([{"supplierInn": "7801234564", "rank": 1}]))

    hits = await retriever(handler).retrieve(make_request(), 5)
    assert len(calls) == 2
    assert [hit.supplier_id for hit in hits.hits] == [ALPHA]


async def test_service_not_ready_twice_is_unavailable() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(MlServiceUnavailableError):
        await retriever(handler).retrieve(make_request(), 5)
    assert len(calls) == 2


async def test_other_errors_are_not_retried() -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(500)

    with pytest.raises(MlServiceError) as raised:
        await retriever(handler).retrieve(make_request(), 5)
    assert raised.value.status == 500
    assert len(calls) == 1


async def test_inferred_items_are_marked_on_the_wire() -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=answer([]))

    inferred = QueryItem(item_id="i1", name="Рис", origin=ItemOrigin.INFERRED)
    hits = await retriever(handler).retrieve(make_request(inferred), 200)
    assert hits.hits == ()
    sent = seen[0]
    assert sent["items"][0]["origin"] == "inferred"
    assert sent["items"][0]["quantity"] is None
    assert sent["options"]["candidateLimit"] == 100
    assert sent["notice"]["region"] == ""


def test_default_clock_is_utc_and_channel_is_semantic() -> None:
    assert utc_now().tzinfo is not None
    assert retriever(lambda request: httpx.Response(200)).channel == "semantic"
