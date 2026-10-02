from uuid import uuid4

import httpx
import pytest

from src.controller.search.api import app
from src.models.supplier_search import SupplierCandidate


class FakeEngine:
    version = "ranker-sha"

    def __init__(self, fails: bool = False) -> None:
        self.fails = fails
        self.calls: list[tuple[str, int]] = []

    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
        self.calls.append((text, limit))
        if self.fails:
            raise RuntimeError("index is not loaded")
        return [
            SupplierCandidate(
                inn="7801234564", category="10.61", profile="", score=0.9, similarity=0.8
            ),
            SupplierCandidate(inn="7707083893", category="", profile="", score=0.4, similarity=0.3),
        ]


@pytest.fixture
def engine() -> FakeEngine:
    fake = FakeEngine()
    app.state.search = fake
    return fake


def request(**notice: object) -> dict[str, object]:
    return {
        "schemaVersion": "1.0",
        "requestId": str(uuid4()),
        "asOf": "2026-10-02T10:00:00Z",
        "notice": {"procedureName": "Крупа гречневая", **notice},
        "items": [{"itemId": "i1", "name": "крупа"}],
        "options": {"candidateLimit": 5},
    }


async def post(body: dict[str, object]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/v1/recommendations", json=body)


async def test_index_candidates_follow_the_ml_contract(engine: FakeEngine) -> None:
    body = request()
    response = await post(body)
    assert response.status_code == 200
    payload = response.json()
    assert payload["requestId"] == body["requestId"]
    assert payload["pipeline"] == {"pipelineVersion": "ranker-sha", "warnings": []}
    assert [(item["supplierInn"], item["rank"]) for item in payload["candidates"]] == [
        ("7801234564", 1),
        ("7707083893", 2),
    ]
    assert payload["candidates"][0]["evidenceRefs"] == ["category:10.61"]
    assert payload["candidates"][0]["matchedItemIds"] == []
    assert engine.calls == [("Крупа гречневая\nкрупа", 5)]


async def test_context_is_reported_as_ignored_by_the_text_model(engine: FakeEngine) -> None:
    response = await post(request(customerInn="7807022750", startPrice="100.00"))
    assert response.json()["pipeline"]["warnings"] == ["contextIgnored"]


async def test_major_schema_mismatch_and_failures_are_explicit(engine: FakeEngine) -> None:
    response = await post({**request(), "schemaVersion": "2.0"})
    assert (response.status_code, response.json()["code"]) == (422, "unsupported_schema")
    engine.fails = True
    failed = await post(request())
    assert (failed.status_code, failed.json()["code"]) == (503, "search_unavailable")
