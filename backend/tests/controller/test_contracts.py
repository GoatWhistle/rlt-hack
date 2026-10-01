import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from src.controller.http.errors import ApiErrorDto
from src.controller.search.dto import RecentSearchesDto, SearchRequestDto, SearchResponseDto
from src.controller.search.mapper import to_query
from src.controller.supplier.dto import SupplierProfileDto
from src.models.candidate import Highlight
from src.models.enums import HighlightCode, ItemType, Locale, PurchaseOutcome
from src.models.purchase import PurchaseRecord, PurchaseSummary
from src.models.search import SearchFilters
from src.models.search_result import SearchResult
from tests.fakes.domain import make_candidate, make_result, make_supplier, uid
from tests.fakes.http import FakeServiceProvider

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"


def load(name: str) -> Any:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def key_paths(value: Any, prefix: str = "$") -> set[str]:
    if isinstance(value, dict):
        found: set[str] = set()
        for key, inner in value.items():
            found.add(f"{prefix}.{key}")
            found |= key_paths(inner, f"{prefix}.{key}")
        return found
    if isinstance(value, list):
        return set().union(*(key_paths(item, f"{prefix}[]") for item in value))
    return set()


def rich_result() -> SearchResult:
    record = PurchaseRecord("32514850391-1", "Поставка круп", PurchaseOutcome.WINNER, ("i1",))
    history = PurchaseSummary(similar=3, wins=1, records=(record,))
    highlights = (
        Highlight(HighlightCode.COVERS_ITEMS, {"matched": 1, "total": 1}),
        Highlight(HighlightCode.IN_STOCK, {"count": 1}),
    )
    candidate = replace(make_candidate(), history=history, highlights=highlights)
    result = make_result(candidate)
    filters = SearchFilters(regions=("78",), item_type=ItemType.GOODS)
    return replace(result, query=replace(result.query, filters=filters))


@pytest.mark.parametrize(
    ("name", "model"),
    [
        ("search/response.example.json", SearchResponseDto),
        ("search/recent.example.json", RecentSearchesDto),
        ("search/error.example.json", ApiErrorDto),
        ("supplier/profile.example.json", SupplierProfileDto),
    ],
)
def test_examples_round_trip_through_dto(name: str, model: type[BaseModel]) -> None:
    example = load(name)
    assert model.model_validate(example).model_dump(by_alias=True, mode="json") == example


def test_request_example_is_a_valid_query() -> None:
    dto = SearchRequestDto.model_validate(load("search/request.example.json"))
    query = to_query(dto, Locale.RU)
    assert query.limit.value == 20
    assert query.filters == SearchFilters(regions=("78",), item_type=ItemType.GOODS)


async def test_search_response_matches_contract_keys(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    provider.searching.result = rich_result()
    created = await client.post("/api/searches", json=load("search/request.example.json"))
    fetched = await client.get(f"/api/searches/{uid('search')}")
    expected = key_paths(load("search/response.example.json"))
    assert key_paths(created.json()) == expected
    assert key_paths(fetched.json()) == expected


async def test_recent_response_matches_contract_keys(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    provider.searching.summaries = (rich_result().summary(),)
    response = await client.get("/api/searches")
    assert key_paths(response.json()) == key_paths(load("search/recent.example.json"))


async def test_profile_response_matches_contract_keys(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/suppliers/{make_supplier().supplier_id}")
    assert key_paths(response.json()) == key_paths(load("supplier/profile.example.json"))


async def test_error_response_matches_contract_keys(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/searches", json={"text": "а" * 4001})
    assert key_paths(response.json()) == key_paths(load("search/error.example.json"))
