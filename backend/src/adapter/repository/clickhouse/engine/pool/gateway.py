import asyncio
import logging
import math
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any

from src.adapter.repository.clickhouse.engine.pool.protocols import PooledGateway, QueryControl

OpenGateway = Callable[[], Awaitable[PooledGateway]]
Slots = asyncio.LifoQueue[PooledGateway | None]
Share = tuple[object, asyncio.Semaphore]

logger = logging.getLogger(__name__)

_share: ContextVar[Share | None] = ContextVar("gateway_pool_share", default=None)


def fair_share(size: int) -> int:
    return max(1, math.ceil(size / 2))


class GatewayPool:
    def __init__(
        self,
        open_gateway: OpenGateway,
        size: int,
        control: QueryControl | None = None,
        share: int | None = None,
    ) -> None:
        if size < 1:
            raise ValueError(size)
        self._open = open_gateway
        self._size = size
        self._share = min(size, share if share is not None else fair_share(size))
        if self._share < 1:
            raise ValueError(share)
        self._control = control
        self._opened: list[PooledGateway] = []
        self._kills: set[asyncio.Future[None]] = set()
        self._slots = self._empty_slots()

    @property
    def size(self) -> int:
        return self._size

    @property
    def share(self) -> int:
        return self._share

    @property
    def opened(self) -> int:
        return len(self._opened)

    @asynccontextmanager
    async def scope(self) -> AsyncIterator[None]:
        token = _share.set((self, asyncio.Semaphore(self._share)))
        try:
            yield
        finally:
            _share.reset(token)

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
        await asyncio.gather(*self._kills, return_exceptions=True)
        opened, self._opened = self._opened, []
        self._slots = self._empty_slots()
        outcomes = await asyncio.gather(
            *(gateway.close() for gateway in opened), return_exceptions=True
        )
        failures = [outcome for outcome in outcomes if isinstance(outcome, BaseException)]
        if failures:
            raise failures[0]

    async def _lease[T](self, operation: Callable[[PooledGateway], Awaitable[T]]) -> T:
        share = _share.get()
        if share is None or share[0] is not self:
            return await self._run(operation)
        async with share[1]:
            return await self._run(operation)

    async def _run[T](self, operation: Callable[[PooledGateway], Awaitable[T]]) -> T:
        slots = self._slots
        gateway = await self._take(slots)
        task = asyncio.ensure_future(operation(gateway))
        task.add_done_callback(_returning(slots, gateway))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if not task.done():
                self._kill(gateway.active_query)
            raise

    def _kill(self, query_id: str | None) -> None:
        if self._control is None or query_id is None:
            return
        kill = asyncio.ensure_future(self._control.kill(query_id))
        self._kills.add(kill)
        kill.add_done_callback(self._killed)

    def _killed(self, kill: asyncio.Future[None]) -> None:
        self._kills.discard(kill)
        if not kill.cancelled() and kill.exception() is not None:
            logger.warning("cancelled query was not killed", exc_info=kill.exception())

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
