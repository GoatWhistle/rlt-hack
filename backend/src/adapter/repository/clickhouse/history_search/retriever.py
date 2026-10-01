import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from src.adapter.repository.clickhouse.history_search.protocols import TextAnalyzer
from src.adapter.repository.clickhouse.history_search.query import participants_statement
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.retrieval.tally import HitTally
from src.adapter.repository.clickhouse.retrieval.terms import needles_for, relevance
from src.adapter.repository.clickhouse.rows import to_uuid
from src.models.query_item import QueryItem, SearchRequest
from src.models.retrieval import RetrievalHits

CHANNEL = "history"
WIN_WEIGHT = 2.0
PARTICIPATION_WEIGHT = 1.0


@dataclass(frozen=True, slots=True)
class Participation:
    lot_id: str
    text: str
    supplier_id: UUID
    won: bool


class ClickHouseHistoryRetriever:
    def __init__(
        self,
        gateway: SqlGateway,
        analyzer: TextAnalyzer,
        database: str = "supplier_search",
        lot_pool: int = 500,
    ) -> None:
        self._gateway = gateway
        self._analyzer = analyzer
        self._db = database
        self._pool = lot_pool

    @property
    def channel(self) -> str:
        return CHANNEL

    async def retrieve(self, request: SearchRequest, limit: int) -> RetrievalHits:
        regions = request.query.filters.regions
        pools = await asyncio.gather(*(self._pool_for(item, regions) for item in request.items))
        tally = await asyncio.to_thread(self._tally, request.items, pools)
        return tally.hits(CHANNEL, limit)

    async def _pool_for(self, item: QueryItem, regions: tuple[str, ...]) -> list[Participation]:
        needles = needles_for(self._analyzer, item.name)
        if not needles:
            return []
        parameters: dict[str, object] = {"needles": list(needles), "pool": self._pool}
        if regions:
            parameters["regions"] = list(regions)
        rows = await self._gateway.select(
            participants_statement(self._db, bool(regions)), parameters
        )
        return [
            Participation(str(row[0]), str(row[1]), to_uuid(row[2]), bool(int(row[3])))
            for row in rows
        ]

    def _tally(self, items: Sequence[QueryItem], pools: Sequence[list[Participation]]) -> HitTally:
        tally = HitTally(accumulate=True)
        for item, pool in zip(items, pools, strict=True):
            lots = {entry.lot_id: entry.text for entry in pool}
            scores = dict(
                zip(lots, relevance(self._analyzer, item.name, list(lots.values())), strict=True)
            )
            for entry in pool:
                score = scores[entry.lot_id]
                if score > 0:
                    weight = WIN_WEIGHT if entry.won else PARTICIPATION_WEIGHT
                    tally.add_lot(entry.supplier_id, item.item_id, entry.lot_id, score * weight)
        return tally
