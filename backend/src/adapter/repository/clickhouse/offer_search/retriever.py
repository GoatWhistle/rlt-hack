import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from src.adapter.repository.clickhouse.offer_search.protocols import TextAnalyzer
from src.adapter.repository.clickhouse.offer_search.query import candidate_query
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.retrieval.tally import HitTally
from src.adapter.repository.clickhouse.retrieval.terms import needles_for, relevance
from src.adapter.repository.clickhouse.rows import to_uuid
from src.models.query_item import QueryItem, SearchRequest
from src.models.retrieval import RetrievalHits

CHANNEL = "lexical"


@dataclass(frozen=True, slots=True)
class OfferText:
    offer_id: UUID
    supplier_id: UUID
    text: str


class ClickHouseLexicalRetriever:
    def __init__(
        self,
        gateway: SqlGateway,
        analyzer: TextAnalyzer,
        database: str = "supplier_search",
        candidate_pool: int = 500,
    ) -> None:
        self._gateway = gateway
        self._analyzer = analyzer
        self._db = database
        self._pool = candidate_pool

    @property
    def channel(self) -> str:
        return CHANNEL

    async def retrieve(self, request: SearchRequest, limit: int) -> RetrievalHits:
        pools = await asyncio.gather(*(self._pool_for(item, request) for item in request.items))
        tally = await asyncio.to_thread(self._tally, request.items, pools)
        return tally.hits(CHANNEL, limit)

    async def _pool_for(self, item: QueryItem, request: SearchRequest) -> list[OfferText]:
        needles = needles_for(self._analyzer, item.name)
        if not needles:
            return []
        query = candidate_query(self._db, needles, request.query.filters, self._pool)
        rows = await self._gateway.select(query.statement, query.parameters)
        return [OfferText(to_uuid(row[0]), to_uuid(row[1]), str(row[2])) for row in rows]

    def _tally(self, items: Sequence[QueryItem], pools: Sequence[list[OfferText]]) -> HitTally:
        tally = HitTally(accumulate=False)
        for item, pool in zip(items, pools, strict=True):
            scores = relevance(self._analyzer, item.name, [offer.text for offer in pool])
            for offer, score in zip(pool, scores, strict=True):
                if score > 0:
                    tally.add_offer(offer.supplier_id, item.item_id, offer.offer_id, score)
        return tally
