import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from src.adapter.repository.clickhouse.history_search.protocols import TextAnalyzer
from src.adapter.repository.clickhouse.history_search.query import participants_query
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.retrieval.similarity import LotSimilarity
from src.adapter.repository.clickhouse.retrieval.tally import HitTally
from src.adapter.repository.clickhouse.retrieval.terms import (
    flags_of,
    index_terms,
    presence_relevance,
)
from src.adapter.repository.clickhouse.rows import to_uuid
from src.models.enums import RetrievalChannel
from src.models.query_item import QueryItem, SearchRequest
from src.models.retrieval import RetrievalHits

CHANNEL = RetrievalChannel.HISTORY


@dataclass(frozen=True, slots=True)
class Participation:
    lot_id: str
    length: int
    supplier_id: UUID
    won: bool
    flags: tuple[bool, ...]


class ClickHouseHistoryRetriever:
    def __init__(
        self,
        gateway: SqlGateway,
        analyzer: TextAnalyzer,
        database: str = "supplier_search",
        lot_pool: int = 500,
        similarity: LotSimilarity | None = None,
    ) -> None:
        self._gateway = gateway
        self._analyzer = analyzer
        self._db = database
        self._pool = lot_pool
        self._similarity = similarity or LotSimilarity()

    @property
    def channel(self) -> str:
        return CHANNEL

    async def retrieve(self, request: SearchRequest, limit: int) -> RetrievalHits:
        regions = request.query.filters.regions
        pools = await asyncio.gather(*(self._pool_for(item, regions) for item in request.items))
        tally = await asyncio.to_thread(self._tally, request.items, pools)
        return tally.hits(CHANNEL, limit)

    async def _pool_for(self, item: QueryItem, regions: tuple[str, ...]) -> list[Participation]:
        terms = index_terms(self._analyzer, item.name)
        if not terms:
            return []
        statement, match = participants_query(self._db, terms, bool(regions))
        parameters: dict[str, object] = {**match.parameters, "pool": self._pool}
        if regions:
            parameters["regions"] = list(regions)
        rows = await self._gateway.select(statement, parameters)
        return [
            Participation(
                str(row[0]), int(str(row[1])), to_uuid(row[2]), bool(row[3]), flags_of(row[4])
            )
            for row in rows
        ]

    def _tally(self, items: Sequence[QueryItem], pools: Sequence[list[Participation]]) -> HitTally:
        tally = HitTally(accumulate=True)
        for item, pool in zip(items, pools, strict=True):
            lots = {entry.lot_id: entry for entry in pool if self._similarity.similar(entry.flags)}
            relevance = presence_relevance(
                [lot.flags for lot in lots.values()], [lot.length for lot in lots.values()]
            )
            scores = dict(zip(lots, relevance, strict=True))
            for entry in pool:
                score = scores.get(entry.lot_id, 0.0)
                if score > 0:
                    weight = self._similarity.weight(won=entry.won)
                    tally.add_lot(entry.supplier_id, item.item_id, entry.lot_id, score * weight)
        return tally
