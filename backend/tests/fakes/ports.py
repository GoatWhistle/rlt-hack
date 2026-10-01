import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.models.offer_evidence import OfferEvidence
from src.models.purchase import PurchaseSummary
from src.models.query_item import QueryItem, SearchRequest
from src.models.retrieval import RetrievalHits
from src.models.search import SearchQuery
from src.models.search_result import SearchResult, SearchSummary
from src.models.supplier import Supplier
from tests.fakes.domain import MOMENT, uid


class PortFailureError(RuntimeError):
    pass


@dataclass(slots=True)
class FakeInterpreter:
    items: tuple[QueryItem, ...] = ()
    calls: list[SearchQuery] = field(default_factory=list)

    async def interpret(self, query: SearchQuery) -> tuple[QueryItem, ...]:
        self.calls.append(query)
        return self.items


@dataclass(slots=True)
class FakeRetriever:
    name: str
    hits: RetrievalHits | None = None
    fails: bool = False
    delay: float = 0.0
    calls: list[tuple[SearchRequest, int]] = field(default_factory=list)

    @property
    def channel(self) -> str:
        return self.name

    async def retrieve(self, request: SearchRequest, limit: int) -> RetrievalHits:
        self.calls.append((request, limit))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fails:
            raise PortFailureError(self.name)
        return self.hits or RetrievalHits(self.name)


@dataclass(slots=True)
class FakeDirectory:
    suppliers: Sequence[Supplier] = ()
    fails: bool = False

    async def get_many(self, supplier_ids: Sequence[UUID]) -> Mapping[UUID, Supplier]:
        if self.fails:
            raise PortFailureError("directory")
        wanted = set(supplier_ids)
        return {item.supplier_id: item for item in self.suppliers if item.supplier_id in wanted}


@dataclass(slots=True)
class FakeOfferCatalog:
    cards: Sequence[OfferEvidence] = ()
    fails_lookup: bool = False
    fails_current: bool = False
    lookups: list[tuple[UUID, ...]] = field(default_factory=list)

    async def get_many(self, offer_ids: Sequence[UUID]) -> Mapping[UUID, OfferEvidence]:
        self.lookups.append(tuple(offer_ids))
        if self.fails_lookup:
            raise PortFailureError("offers")
        wanted = set(offer_ids)
        return {card.offer.offer_id: card for card in self.cards if card.offer.offer_id in wanted}

    async def current_for(
        self, supplier_ids: Sequence[UUID], per_supplier: int
    ) -> Mapping[UUID, tuple[OfferEvidence, ...]]:
        if self.fails_current:
            raise PortFailureError("current")
        grouped: dict[UUID, tuple[OfferEvidence, ...]] = {}
        for supplier_id in supplier_ids:
            owned = tuple(
                card
                for card in self.cards
                if card.offer.supplier_id == supplier_id and card.is_current
            )
            if owned:
                grouped[supplier_id] = owned[:per_supplier]
        return grouped


@dataclass(slots=True)
class FakeHistory:
    summaries: Mapping[UUID, PurchaseSummary] = field(default_factory=dict)
    fails: bool = False

    async def summarize(
        self, supplier_ids: Sequence[UUID], items: Sequence[QueryItem], records: int
    ) -> Mapping[UUID, PurchaseSummary]:
        if self.fails:
            raise PortFailureError("history")
        return {key: value for key, value in self.summaries.items() if key in supplier_ids}


@dataclass(slots=True)
class FakeArchive:
    stored: dict[UUID, SearchResult] = field(default_factory=dict)
    fails: bool = False
    delay: float = 0.0

    async def save(self, result: SearchResult) -> None:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fails:
            raise PortFailureError("archive")
        self.stored[result.search_id] = result

    async def get(self, search_id: UUID) -> SearchResult | None:
        return self.stored.get(search_id)

    async def recent(self, limit: int) -> tuple[SearchSummary, ...]:
        ordered = sorted(self.stored.values(), key=lambda item: item.created_at, reverse=True)
        return tuple(item.summary() for item in ordered[:limit])


@dataclass(slots=True)
class FixedClock:
    moment: datetime = MOMENT

    def now(self) -> datetime:
        return self.moment


@dataclass(slots=True)
class SequentialIds:
    issued: int = 0

    def new(self) -> UUID:
        self.issued += 1
        return uid(f"search:{self.issued}")
