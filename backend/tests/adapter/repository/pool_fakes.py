import asyncio
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from clickhouse_connect.driver.exceptions import OperationalError
from urllib3.exceptions import ProtocolError

from src.adapter.repository.clickhouse.engine.gateway import ConnectGateway
from src.adapter.repository.clickhouse.engine.pool.gateway import GatewayPool
from src.adapter.repository.errors import RepositoryUnavailableError

Settings = Mapping[str, Any] | None


@dataclass(slots=True)
class QueryResult:
    result_rows: list[list[Any]]


@dataclass(slots=True)
class InsertContext:
    table: str
    column_names: list[str]
    settings: Settings
    column_types: list[str]
    data: Sequence[Sequence[Any]] | None = None


@dataclass(slots=True)
class Activity:
    delay: float = 0.02
    active: int = 0
    peak: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def enter(self) -> None:
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)

    def leave(self) -> None:
        with self.lock:
            self.active -= 1


class FakeDriver:
    def __init__(self, activity: Activity, number: int) -> None:
        self.activity = activity
        self.number = number
        self.closed = False
        self.close_failure: BaseException | None = None
        self.failure: BaseException | None = None
        self.gate: threading.Event | None = None
        self.statements: list[str] = []
        self.query_ids: list[str] = []
        self.described: list[str] = []
        self.inserted_types: list[Sequence[str]] = []

    def query(
        self, statement: str, parameters: Mapping[str, Any], settings: Settings = None
    ) -> QueryResult:
        self._work(statement, settings)
        return QueryResult([[self.number, statement]])

    def command(
        self, statement: str, parameters: Mapping[str, Any], settings: Settings = None
    ) -> None:
        self._work(statement, settings)

    def create_insert_context(
        self, table: str, column_names: list[str], settings: Settings = None
    ) -> InsertContext:
        self.described.append(table)
        types = [f"type:{name}" for name in column_names]
        return InsertContext(table, column_names, settings, types)

    def insert(
        self,
        table: str | None = None,
        data: Sequence[Sequence[Any]] | None = None,
        column_names: list[str] | None = None,
        column_types: Sequence[str] | None = None,
        settings: Settings = None,
        context: InsertContext | None = None,
    ) -> None:
        if context is not None:
            table, settings, column_types = context.table, context.settings, context.column_types
        self.inserted_types.append(tuple(column_types or ()))
        self._work(str(table), settings)

    def close(self) -> None:
        if self.close_failure is not None:
            raise self.close_failure
        self.closed = True

    def _work(self, statement: str, settings: Settings) -> None:
        self.query_ids.append(str((settings or {}).get("query_id", "")))
        self.activity.enter()
        try:
            if self.gate is not None:
                self.gate.wait(5)
            time.sleep(self.activity.delay)
            self.statements.append(statement)
            if self.failure is not None:
                raise self.failure
        finally:
            self.activity.leave()


class Driver:
    def __init__(self) -> None:
        self.activity = Activity()
        self.drivers: list[FakeDriver] = []
        self.refusals = 0

    async def open(self) -> ConnectGateway:
        await asyncio.sleep(0)
        if self.refusals:
            self.refusals -= 1
            raise RepositoryUnavailableError("refused")
        driver = FakeDriver(self.activity, len(self.drivers))
        self.drivers.append(driver)
        return ConnectGateway(driver)


@dataclass(slots=True)
class KillSwitch:
    gates: list[threading.Event] = field(default_factory=list)
    killed: list[str] = field(default_factory=list)
    failure: BaseException | None = None

    async def kill(self, query_id: str) -> None:
        self.killed.append(query_id)
        if self.failure is not None:
            raise self.failure
        for gate in self.gates:
            gate.set()


def transport_error() -> OperationalError:
    error = OperationalError("Error executing HTTP request")
    error.__cause__ = ProtocolError("connection reset")
    return error


async def select_many(pool: GatewayPool, count: int) -> list[list[tuple[Any, ...]]]:
    return await asyncio.gather(*(pool.select(f"SELECT {index}") for index in range(count)))
