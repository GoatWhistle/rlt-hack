"""Реализация SqlGateway на встроенном движке chDB.

Позволяет проверять SQL репозиториев и миграции без сервера ClickHouse.
Параметры запросов подставляются литералами: chDB принимает запрос строкой.
Движок синхронный, поэтому запросы уходят в отдельный поток — как и драйвер
ClickHouse в рабочем шлюзе.
"""

import asyncio
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

_PLACEHOLDER = re.compile(r"\{(\w+):([^{}]+)\}")


class ChdbGateway:
    def __init__(self, session: Any) -> None:
        self._session = session
        self._lock = asyncio.Lock()

    async def command(self, statement: str, parameters: Mapping[str, Any] | None = None) -> None:
        await self._query(_bind(statement, parameters))

    async def select(
        self,
        statement: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> list[tuple[Any, ...]]:
        output = str(await self._query(_bind(statement, parameters), "JSONCompactEachRow"))
        return [tuple(json.loads(line)) for line in output.splitlines() if line.strip()]

    async def insert(
        self,
        table: str,
        column_names: Sequence[str],
        rows: Sequence[Sequence[Any]],
    ) -> None:
        if not rows:
            return
        columns = ", ".join(column_names)
        payload = "\n".join(
            json.dumps(
                {name: _json_value(value) for name, value in zip(column_names, row, strict=True)},
                ensure_ascii=False,
            )
            for row in rows
        )
        await self._query(f"INSERT INTO {table} ({columns}) FORMAT JSONEachRow {payload}")

    async def close(self) -> None:
        await asyncio.to_thread(self._session.close)

    async def _query(self, statement: str, output: str | None = None) -> Any:
        async with self._lock:
            if output is None:
                return await asyncio.to_thread(self._session.query, statement)
            return await asyncio.to_thread(self._session.query, statement, output)


def _bind(statement: str, parameters: Mapping[str, Any] | None) -> str:
    if not parameters:
        return statement

    def replace(match: re.Match[str]) -> str:
        name, declared = match.group(1), match.group(2).strip()
        if name not in parameters:
            return match.group(0)
        return _literal(parameters[name], declared)

    return _PLACEHOLDER.sub(replace, statement)


def _literal(value: Any, declared: str) -> str:
    if declared.startswith("Array("):
        inner = declared[len("Array(") : -1]
        if not value:
            return f"CAST([], 'Array({inner})')"
        return "[" + ", ".join(_literal(item, inner) for item in value) + "]"
    if declared == "UUID":
        return f"toUUID('{value}')"
    if declared.startswith("DateTime64"):
        return f"toDateTime64('{_timestamp(value)}', 3, 'UTC')"
    if declared.startswith(("UInt", "Int", "Float", "Decimal")):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def _timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    return str(value)


def _json_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return _timestamp(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, tuple):
        return list(value)
    return value
