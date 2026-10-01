import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

from src.adapter.repository.clickhouse.pool.gateway import OpenGateway
from src.adapter.repository.clickhouse.pool.protocols import PooledGateway

KILL_QUERY = "KILL QUERY WHERE query_id = {query_id:String} ASYNC"


class ControlChannel:
    def __init__(self, open_gateway: OpenGateway) -> None:
        self._open = open_gateway
        self._gateway: PooledGateway | None = None
        self._lock = asyncio.Lock()

    async def kill(self, query_id: str) -> None:
        await self.command(KILL_QUERY, {"query_id": query_id})

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

    async def aclose(self) -> None:
        gateway, self._gateway = self._gateway, None
        if gateway is not None:
            await gateway.close()

    async def _resolve(self) -> PooledGateway:
        if self._gateway is None:
            async with self._lock:
                if self._gateway is None:
                    self._gateway = await self._open()
        return self._gateway
