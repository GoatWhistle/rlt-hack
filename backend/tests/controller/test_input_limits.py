import httpx
import pytest

from src.controller.search.dto import MAX_REGIONS, REGION_MAX_LENGTH
from tests.fakes.http import FakeServiceProvider

LONG = "x" * 300


@pytest.mark.parametrize(
    "regions",
    [["78"] * (MAX_REGIONS + 1), ["р" * (REGION_MAX_LENGTH + 1)]],
    ids=["too-many", "too-long"],
)
async def test_rejects_oversized_regions(
    client: httpx.AsyncClient, provider: FakeServiceProvider, regions: list[str]
) -> None:
    response = await client.post(
        "/api/searches", json={"text": "рис", "filters": {"regions": regions}}
    )
    assert (response.status_code, response.json()["code"]) == (422, "invalid_request")
    assert provider.searching.queries == []


async def test_accepts_regions_within_limits(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    regions = [f"r{index}" for index in range(MAX_REGIONS)]
    response = await client.post(
        "/api/searches", json={"text": "рис", "filters": {"regions": regions}}
    )
    assert response.status_code == 201
    assert len(provider.searching.queries[0].filters.regions) == MAX_REGIONS


@pytest.mark.parametrize(
    ("path", "message"),
    [
        (f"/api/searches/{LONG}", "search not found"),
        (f"/api/suppliers/{LONG}", "supplier not found"),
    ],
)
async def test_not_found_message_does_not_echo_input(
    client: httpx.AsyncClient, path: str, message: str
) -> None:
    response = await client.get(path)
    assert response.status_code == 404
    assert response.json()["message"] == message
    assert LONG not in response.text
