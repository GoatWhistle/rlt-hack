import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any
from uuid import uuid4

import httpx
import pytest

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.errors import RepositoryError, RepositoryUnavailableError
from src.application.api import ApiContainer
from src.application.config import AppConfig, MlServiceConfig, SearchConfig
from src.application.deferred_gateway import DeferredGateway
from src.controller.http.app import create_app
from src.controller.http.settings import ApiSettings
from src.service.errors import StorageUnavailableError


class RecordingGateway:
    def __init__(self, failing: bool = False, rows: list[tuple[Any, ...]] | None = None) -> None:
        self.failing = failing
        self.rows = [(1,)] if rows is None else rows
        self.statements: list[str] = []

    async def command(self, statement: str, parameters: Mapping[str, Any] | None = None) -> None:
        self.statements.append(statement)

    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        if self.failing:
            raise ConnectionError(statement)
        self.statements.append(statement)
        return self.rows

    async def insert(
        self, table: str, column_names: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None:
        self.statements.append(table)


class Connector:
    def __init__(self, gateway: RecordingGateway) -> None:
        self.gateway = gateway
        self.connections = 0
        self.released = 0

    async def connect(self) -> SqlGateway:
        self.connections += 1
        await asyncio.sleep(0)
        return self.gateway

    async def release(self) -> None:
        self.released += 1


def container(config: AppConfig, gateway: RecordingGateway | None = None) -> ApiContainer:
    connector = Connector(gateway or RecordingGateway())
    return ApiContainer(config, connector.connect, connector.release)


def channels(api: ApiContainer) -> list[str]:
    return [retriever.channel for retriever in api.retrievers()]


async def test_deferred_gateway_connects_once_on_first_use() -> None:
    connector = Connector(RecordingGateway())
    gateway = DeferredGateway(connector.connect)
    assert connector.connections == 0
    await asyncio.gather(gateway.select("SELECT 1"), gateway.command("OPTIMIZE"))
    await gateway.insert("t", ("a",), [(1,)])
    assert connector.connections == 1
    assert connector.gateway.statements == ["SELECT 1", "OPTIMIZE", "t"]


def test_channels_follow_configuration() -> None:
    config = AppConfig()
    assert channels(container(config)) == ["lexical", "history"]
    quiet = replace(config, search=SearchConfig(history_enabled=False))
    assert channels(container(quiet)) == ["lexical"]
    semantic = replace(config, ml_service=MlServiceConfig(enabled=True))
    assert channels(container(semantic)) == ["lexical", "history", "semantic"]


async def test_services_are_assembled_without_touching_the_database() -> None:
    gateway = RecordingGateway()
    api = container(AppConfig(), gateway)
    assert api.database == "supplier_search"
    assert await api.supplier_search() is not None
    assert await api.supplier_profiles() is not None
    assert gateway.statements == []


@pytest.mark.parametrize(("failing", "ready"), [(False, True), (True, False)])
async def test_health_probes_clickhouse(failing: bool, ready: bool) -> None:
    api = container(AppConfig(), RecordingGateway(failing=failing))
    readiness = await (await api.health()).readiness()
    assert readiness.ready is ready
    names = [component.name for component in readiness.components]
    assert names == ["clickhouse", "catalog", "history", "novelty"]
    required = [component.required for component in readiness.components]
    assert required == [True, False, False, False]


async def test_ml_channel_is_an_optional_component() -> None:
    config = replace(AppConfig(), ml_service=MlServiceConfig(enabled=True))
    api = container(config, RecordingGateway(rows=[(1,)]))
    readiness = await (await api.health()).readiness()
    assert readiness.ready
    assert readiness.degraded == ("semantic",)
    await api.aclose()


async def test_closing_releases_the_database_and_the_ml_client() -> None:
    connector = Connector(RecordingGateway())
    config = replace(AppConfig(), ml_service=MlServiceConfig(enabled=True))
    api = ApiContainer(config, connector.connect, connector.release)
    api.retrievers()
    api.retrievers()
    await api.aclose()
    await api.aclose()
    assert connector.released == 2
    await ApiContainer(AppConfig(), connector.connect).aclose()


async def refuse() -> SqlGateway:
    raise RepositoryUnavailableError("connection refused")


async def test_deferred_gateway_reports_storage_outage_to_services() -> None:
    gateway = DeferredGateway(refuse)
    with pytest.raises(StorageUnavailableError):
        await gateway.select("SELECT 1")
    with pytest.raises(StorageUnavailableError):
        await gateway.command("OPTIMIZE")
    with pytest.raises(StorageUnavailableError):
        await gateway.insert("t", ("a",), [(1,)])


async def test_deferred_gateway_keeps_other_repository_errors() -> None:
    async def broken() -> SqlGateway:
        raise RepositoryError("bad sql")

    with pytest.raises(RepositoryError):
        await DeferredGateway(broken).select("SELECT 1")


async def test_unreachable_clickhouse_returns_503() -> None:
    app = create_app(ApiContainer(AppConfig(), refuse), ApiSettings())
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            for path in (
                "/api/searches",
                f"/api/searches/{uuid4()}",
                f"/api/suppliers/{uuid4()}",
                "/api/uploads",
                f"/api/uploads/{uuid4()}",
            ):
                response = await http.get(path)
                assert (response.status_code, response.json()["code"]) == (
                    503,
                    "storage_unavailable",
                ), path
            searched = await http.post("/api/searches", json={"text": "рис 5 кг"})
            assert (searched.status_code, searched.json()["code"]) == (503, "search_unavailable")
            assert (await http.get("/api/health/ready")).status_code == 503


async def test_uploads_use_separate_gateway() -> None:
    interactive = Connector(RecordingGateway(rows=[]))
    background = Connector(RecordingGateway(rows=[]))
    control = Connector(RecordingGateway())
    api = ApiContainer(
        AppConfig(),
        interactive.connect,
        background=background.connect,
        control=control.connect,
    )
    uploads = await api.procurement_uploads()
    await uploads.start()
    try:
        for _ in range(100):
            if background.gateway.statements:
                break
            await asyncio.sleep(0.01)
        await uploads.recent("a" * 32, 5)
    finally:
        await uploads.stop()
    assert "upload_lots" in background.gateway.statements[0]
    assert len(interactive.gateway.statements) == 1
    assert "uploads" in interactive.gateway.statements[0]
    assert (await (await api.health()).readiness()).ready
    assert len(control.gateway.statements) == 4
