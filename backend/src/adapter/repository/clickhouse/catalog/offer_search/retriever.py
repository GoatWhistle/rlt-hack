import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from src.adapter.repository.clickhouse.catalog.offer_search.protocols import TextAnalyzer
from src.adapter.repository.clickhouse.catalog.offer_search.query import candidate_query
from src.adapter.repository.clickhouse.engine.rows import to_uuid
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.search.retrieval.tally import HitTally
from src.adapter.repository.clickhouse.search.retrieval.terms import (
    flags_of,
    index_terms,
    presence_relevance,
)
from src.models.enums import RetrievalChannel
from src.models.ranking.retrieval import RetrievalHits
from src.models.search.query_item import QueryItem, SearchRequest

CHANNEL = RetrievalChannel.LEXICAL


@dataclass(frozen=True, slots=True)
class OfferMatch:
    offer_id: UUID
    supplier_id: UUID
    length: int
    flags: tuple[bool, ...]
    name: str


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

    async def _pool_for(self, item: QueryItem, request: SearchRequest) -> list[OfferMatch]:
        terms = index_terms(self._analyzer, item.name)
        if not terms:
            return []
        query = candidate_query(self._db, terms, request.query.filters, self._pool)
        rows = await self._gateway.select(query.statement, query.parameters)
        return [
            OfferMatch(
                to_uuid(row[0]), to_uuid(row[1]), int(str(row[2])), flags_of(row[-1]), str(row[3])
            )
            for row in rows
        ]

    def _tally(self, items: Sequence[QueryItem], pools: Sequence[list[OfferMatch]]) -> HitTally:
        tally = HitTally(accumulate=False)
        names = {offer.name for pool in pools for offer in pool}
        title_terms_by_name = {name: set(self._analyzer.analyze(name)) for name in names}
        for item, pool in zip(items, pools, strict=True):
            query_terms = set(self._analyzer.analyze(item.name))
            scores = presence_relevance(
                [offer.flags for offer in pool], [offer.length for offer in pool]
            )
            for offer, score in zip(pool, scores, strict=True):
                title_terms = title_terms_by_name[offer.name]
                if score > 0 and query_terms & title_terms:
                    tally.add_offer(
                        offer.supplier_id,
                        item.item_id,
                        offer.offer_id,
                        score,
                        inferred=query_terms != title_terms,
                    )
        return tally
