"""Интерфейс исполнения SQL, который потребляют миграции и репозитории.

Абстракция нужна, чтобы один и тот же SQL проверялся как на сервере ClickHouse,
так и на встроенном движке chDB в тестах.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class SqlGateway(Protocol):
    async def command(
        self,
        statement: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> None:
        """Выполняет запрос без чтения результата: DDL и INSERT ... SELECT."""

    async def select(
        self,
        statement: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> list[tuple[Any, ...]]:
        """Возвращает строки результата."""

    async def insert(
        self,
        table: str,
        column_names: Sequence[str],
        rows: Sequence[Sequence[Any]],
    ) -> None:
        """Вставляет строки в таблицу с указанным порядком колонок."""
