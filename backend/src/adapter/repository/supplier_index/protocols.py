from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from src.models.search.search_context import SearchContext


class SqlGateway(Protocol):
    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]: ...

    async def insert(
        self, table: str, column_names: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None: ...


class CandidateRanking(Protocol):
    version: str

    def rank(
        self,
        text,
        cards,
        dense,
        lexical,
        scores,
        dense_order,
        lexical_order,
        context: SearchContext | None = None,
    ) -> tuple[list[str], dict[str, int], dict[str, float], dict[str, list[str]]]: ...


class SimilarityScorer(Protocol):
    async def score(self, index_id: str, vector: list[float], card_count: int) -> list[float]: ...
