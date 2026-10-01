from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class SqlGateway(Protocol):
    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]: ...

    async def insert(
        self, table: str, column_names: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None: ...


class CandidateRanking(Protocol):
    def rank(
        self, text, cards, dense, lexical, scores, dense_order, lexical_order
    ) -> tuple[list[str], dict[str, int], dict[str, float]]: ...
