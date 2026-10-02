import httpx
import pytest

from src.controller.http.app import create_app
from src.controller.http.protocols import BackgroundTask
from src.controller.http.settings import ApiSettings
from src.controller.http.state import Services
from tests.fakes.http import FakeReadiness, FakeServiceProvider


class BrokenProvider(FakeServiceProvider):
    async def health(self) -> FakeReadiness:
        raise RuntimeError("cannot connect")


async def test_lifespan_resolves_services_once_and_closes_provider() -> None:
    provider = FakeServiceProvider()
    app = create_app(provider, ApiSettings())
    async with app.router.lifespan_context(app):
        assert app.state.services == Services(
            supplier_search=provider.searching,
            supplier_profiles=provider.profiles,
            procurement_uploads=provider.uploads,
            health=provider.readiness,
            background=(provider.uploads,),
        )
        assert (provider.uploads.started, provider.uploads.stopped) == (1, 0)
        assert provider.closed == 0
    assert (provider.uploads.started, provider.uploads.stopped) == (1, 1)
    assert provider.closed == 1


class Recorder:
    def __init__(self, name: str, events: list[str]) -> None:
        self._name = name
        self._events = events

    async def start(self) -> None:
        self._events.append(f"start {self._name}")

    async def stop(self) -> None:
        self._events.append(f"stop {self._name}")


async def test_lifespan_runs_every_background_task() -> None:
    events: list[str] = []

    class TwoTasks(FakeServiceProvider):
        async def background(self) -> tuple[BackgroundTask, ...]:
            return (Recorder("uploads", events), Recorder("metrics", events))

    app = create_app(TwoTasks(), ApiSettings())
    async with app.router.lifespan_context(app):
        assert events == ["start uploads", "start metrics"]
    assert events[2:] == ["stop metrics", "stop uploads"]


async def test_failed_startup_still_closes_provider() -> None:
    provider = BrokenProvider()
    app = create_app(provider, ApiSettings())
    with pytest.raises(RuntimeError):
        async with app.router.lifespan_context(app):
            pass
    assert provider.closed == 1


async def test_docs_can_be_disabled() -> None:
    app = create_app(FakeServiceProvider(), ApiSettings(docs_enabled=False))
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            assert (await client.get("/api/docs")).status_code == 404
            assert (await client.get("/api/openapi.json")).status_code == 404


def test_settings_reach_openapi() -> None:
    app = create_app(FakeServiceProvider(), ApiSettings(title="Test", version="9.9.9"))
    assert app.title == "Test"
    assert app.version == "9.9.9"
    assert app.docs_url == "/api/docs"
    assert app.openapi_url == "/api/openapi.json"
