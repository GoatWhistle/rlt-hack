import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

import pytest

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.application.api import ApiContainer
from src.application.config import AppConfig, MlServiceConfig, SearchConfig
from src.application.deferred_gateway import DeferredGateway


class RecordingGateway:
    def __init__(self, failing: bool = False) -> None:
        self.failing = failing
        self.statements: list[str] = []

    async def command(self, statement: str, parameters: Mapping[str, Any] | None = None) -> None:
        self.statements.append(statement)

    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        if self.failing:
            raise ConnectionError(statement)
        self.statements.append(statement)
        return [(1,)]

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
    assert [component.name for component in readiness.components] == ["clickhouse"]


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
