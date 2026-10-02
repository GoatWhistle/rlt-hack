from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from src.adapter.repository.clickhouse.history_search.retriever import ClickHouseHistoryRetriever
from src.adapter.repository.clickhouse.offer_search.retriever import ClickHouseLexicalRetriever
from src.adapter.text.analyzer.analyzer import RussianAnalyzer
from tests.fakes.domain import make_item, make_request, uid

POOL = 500


@dataclass(slots=True)
class CountingAnalyzer:
    inner: RussianAnalyzer = field(default_factory=RussianAnalyzer)
    analyzed: list[str] = field(default_factory=list)

    def analyze(self, text: str) -> tuple[str, ...]:
        self.analyzed.append(text)
        return self.inner.analyze(text)

    def prefixes(self, text: str) -> tuple[str, ...]:
        self.analyzed.append(text)
        return self.inner.prefixes(text)


@dataclass(slots=True)
class PoolGateway:
    rows: list[tuple[Any, ...]]
    statements: list[str] = field(default_factory=list)

    async def command(self, statement: str, parameters: Mapping[str, Any] | None = None) -> None:
        self.statements.append(statement)

    async def select(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> list[tuple[Any, ...]]:
        self.statements.append(statement)
        return self.rows

    async def insert(
        self, table: str, column_names: Sequence[str], rows: Sequence[Sequence[Any]]
    ) -> None:
        self.statements.append(table)


ITEMS = (make_item("i1", "Крупа гречневая ядрица"), make_item("i2", "Рис шлифованный"))


async def test_offer_texts_are_not_analyzed_in_python() -> None:
    rows = [
        (uid(f"offer-{index}"), uid(f"supplier-{index % 50}"), 12, [index % 2 == 0, True])
        for index in range(POOL)
    ]
    analyzer = CountingAnalyzer()
    retriever = ClickHouseLexicalRetriever(PoolGateway(rows), analyzer, candidate_pool=POOL)
    hits = await retriever.retrieve(make_request(*ITEMS), 20)
    assert len(analyzer.analyzed) == len(ITEMS)
    assert hits.hits


async def test_lot_texts_are_not_analyzed_in_python() -> None:
    rows = [
        (f"L{index}", 9, uid(f"supplier-{index % 50}"), index % 3 == 0, [True, True, False])
        for index in range(POOL)
    ]
    analyzer = CountingAnalyzer()
    retriever = ClickHouseHistoryRetriever(PoolGateway(rows), analyzer, lot_pool=POOL)
    hits = await retriever.retrieve(make_request(*ITEMS), 20)
    assert len(analyzer.analyzed) == len(ITEMS)
    assert hits.hits
