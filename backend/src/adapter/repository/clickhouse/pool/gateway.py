import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from src.adapter.repository.clickhouse.pool.protocols import PooledGateway

OpenGateway = Callable[[], Awaitable[PooledGateway]]
Slots = asyncio.LifoQueue[PooledGateway | None]


class GatewayPool:
    def __init__(self, open_gateway: OpenGateway, size: int) -> None:
        if size < 1:
            raise ValueError(size)
        self._open = open_gateway
        self._size = size
        self._opened: list[PooledGateway] = []
        self._slots = self._empty_slots()

    @property
    def size(self) -> int:
        return self._size

    @property
    def opened(self) -> int:
        return len(self._opened)

    async def command(self, statement: str, parameters: Mapping[str, Any] | None = None) -> None:
        await self._lease(lambda gateway: gateway.command(statement, parameters))

    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        return await self._lease(lambda gateway: gateway.select(statement, parameters))

    async def insert(
        self, table: str, column_names: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None:
        await self._lease(lambda gateway: gateway.insert(table, column_names, rows))

    async def aclose(self) -> None:
        opened, self._opened = self._opened, []
        self._slots = self._empty_slots()
        outcomes = await asyncio.gather(
            *(gateway.close() for gateway in opened), return_exceptions=True
        )
        failures = [outcome for outcome in outcomes if isinstance(outcome, BaseException)]
        if failures:
            raise failures[0]

    async def _lease[T](self, operation: Callable[[PooledGateway], Awaitable[T]]) -> T:
        slots = self._slots
        gateway = await self._take(slots)
        task = asyncio.ensure_future(operation(gateway))
        task.add_done_callback(_returning(slots, gateway))
        return await asyncio.shield(task)

    async def _take(self, slots: Slots) -> PooledGateway:
        slot = await slots.get()
        if slot is not None:
            return slot
        try:
            gateway = await self._open()
        except BaseException:
            slots.put_nowait(None)
            raise
        self._opened.append(gateway)
        return gateway

    def _empty_slots(self) -> Slots:
        slots: Slots = asyncio.LifoQueue()
        for _ in range(self._size):
            slots.put_nowait(None)
        return slots


def _returning(slots: Slots, gateway: PooledGateway) -> Callable[[asyncio.Future[Any]], None]:
    def release(task: asyncio.Future[Any]) -> None:
        slots.put_nowait(gateway)
        if not task.cancelled():
            task.exception()

    return release
