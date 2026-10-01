from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class PooledGateway(Protocol):
    async def command(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> None: ...

    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]: ...

    async def insert(
        self, table: str, column_names: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None: ...

    async def close(self) -> None: ...
