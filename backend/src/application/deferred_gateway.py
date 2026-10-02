import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Mapping, Sequence
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.errors import RepositoryUnavailableError
from src.service.errors import StorageUnavailableError
from src.service.supplier_search.protocols import WorkShare

Connect = Callable[[], Awaitable[SqlGateway]]
ResolveShare = Callable[[], Awaitable[WorkShare]]


@contextmanager
def storage_outage() -> Iterator[None]:
    try:
        yield
    except RepositoryUnavailableError as error:
        raise StorageUnavailableError from error


class DeferredGateway:
    def __init__(self, connect: Connect) -> None:
        self._connect = connect
        self._gateway: SqlGateway | None = None
        self._lock = asyncio.Lock()

    async def command(self, statement: str, parameters: Mapping[str, Any] | None = None) -> None:
        with storage_outage():
            await (await self._resolve()).command(statement, parameters)

    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        with storage_outage():
            return await (await self._resolve()).select(statement, parameters)

    async def insert(
        self, table: str, column_names: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None:
        with storage_outage():
            await (await self._resolve()).insert(table, column_names, rows)

    async def _resolve(self) -> SqlGateway:
        if self._gateway is None:
            async with self._lock:
                if self._gateway is None:
                    self._gateway = await self._connect()
        return self._gateway


class DeferredShare:
    def __init__(self, resolve: ResolveShare) -> None:
        self._resolve = resolve

    @asynccontextmanager
    async def scope(self) -> AsyncIterator[None]:
        share = await self._resolve()
        async with share.scope():
            yield
