"""Исполнение SQL через clickhouse-connect.

Драйвер синхронный: каждый запрос уходит в отдельный поток, поэтому обходы
источников не блокируют событийный цикл. Соединение драйвера не рассчитано на
одновременное использование, поэтому запросы одного шлюза сериализованы
блокировкой: конкурентность даёт сеть и разбор документов, а не запись.
"""

import asyncio
from collections.abc import Callable, Mapping, Sequence
from types import TracebackType
from typing import Any
from uuid import uuid4

from clickhouse_connect.driver.exceptions import OperationalError
from urllib3.exceptions import HTTPError as TransportError

from src.adapter.repository.errors import RepositoryError, RepositoryUnavailableError


class ConnectGateway:
    """Обёртка клиента clickhouse-connect под интерфейс SqlGateway."""

    def __init__(self, client: Any, comment: Callable[[], str | None] | None = None) -> None:
        self._client = client
        self._comment = comment
        self._lock = asyncio.Lock()
        self._query_id: str | None = None

    @property
    def active_query(self) -> str | None:
        return self._query_id

    async def command(
        self,
        statement: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> None:
        await self._run(self._client.command, statement, parameters=dict(parameters or {}))

    async def select(
        self,
        statement: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> list[tuple[Any, ...]]:
        result = await self._run(self._client.query, statement, parameters=dict(parameters or {}))
        return [tuple(row) for row in result.result_rows]

    async def insert(
        self,
        table: str,
        column_names: Sequence[str],
        rows: Sequence[Sequence[Any]],
    ) -> None:
        if not rows:
            return
        await self._run(
            self._client.insert,
            table,
            [list(row) for row in rows],
            column_names=list(column_names),
        )

    async def close(self) -> None:
        await asyncio.to_thread(self._client.close)

    async def _run(self, call: Any, *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            query_id = uuid4().hex
            self._query_id = query_id
            try:
                with _translated_errors():
                    return await asyncio.to_thread(
                        call, *args, settings=self._settings(query_id), **kwargs
                    )
            finally:
                self._query_id = None

    def _settings(self, query_id: str) -> dict[str, str]:
        settings = {"query_id": query_id}
        comment = self._comment() if self._comment is not None else None
        if comment:
            settings["log_comment"] = comment
        return settings


class _translated_errors:
    """Переводит ошибки драйвера в ошибки слоя репозитория."""

    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc is None:
            return False
        if isinstance(exc, OSError) or _transport_failure(exc):
            raise RepositoryUnavailableError(str(exc)) from exc
        if type(exc).__module__.startswith("clickhouse_connect"):
            raise RepositoryError(str(exc)) from exc
        return False


def _transport_failure(exc: BaseException) -> bool:
    return isinstance(exc, OperationalError) and isinstance(exc.__cause__, TransportError | OSError)
