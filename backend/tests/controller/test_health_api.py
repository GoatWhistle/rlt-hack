import httpx

from src.models.enums import ComponentState
from tests.fakes.http import FakeServiceProvider


async def test_live_is_always_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_when_every_component_is_up(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"ready": True, "components": [{"name": "clickhouse", "state": "up"}]}


async def test_not_ready_when_a_component_is_down(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    provider.readiness.states = {"clickhouse": ComponentState.UP, "ml": ComponentState.DOWN}
    response = await client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json() == {
        "ready": False,
        "components": [
            {"name": "clickhouse", "state": "up"},
            {"name": "ml", "state": "down"},
        ],
    }
