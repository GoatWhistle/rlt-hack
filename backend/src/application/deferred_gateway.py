import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from src.adapter.repository.clickhouse.protocols import SqlGateway

Connect = Callable[[], Awaitable[SqlGateway]]


class DeferredGateway:
    def __init__(self, connect: Connect) -> None:
        self._connect = connect
        self._gateway: SqlGateway | None = None
        self._lock = asyncio.Lock()

    async def command(self, statement: str, parameters: Mapping[str, Any] | None = None) -> None:
        await (await self._resolve()).command(statement, parameters)

    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        return await (await self._resolve()).select(statement, parameters)

    async def insert(
        self, table: str, column_names: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None:
        await (await self._resolve()).insert(table, column_names, rows)

    async def _resolve(self) -> SqlGateway:
        if self._gateway is None:
            async with self._lock:
                if self._gateway is None:
                    self._gateway = await self._connect()
        return self._gateway
