from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.models.archive_roster import ArchiveRoster
from src.models.offer_evidence import OfferEvidence
from src.models.purchase import PurchaseSummary
from src.models.query_item import QueryItem, SearchRequest
from src.models.retrieval import RetrievalHits
from src.models.search import SearchQuery
from src.models.search_result import SearchResult, SearchSummary
from src.models.supplier import Supplier


class QueryInterpreter(Protocol):
    async def interpret(self, query: SearchQuery) -> tuple[QueryItem, ...]: ...


class CandidateRetriever(Protocol):
    @property
    def channel(self) -> str: ...

    async def retrieve(self, request: SearchRequest, limit: int) -> RetrievalHits: ...


class SupplierDirectory(Protocol):
    async def get_many(self, supplier_ids: Sequence[UUID]) -> Mapping[UUID, Supplier]: ...


class OfferCatalog(Protocol):
    async def get_many(self, offer_ids: Sequence[UUID]) -> Mapping[UUID, OfferEvidence]: ...

    async def current_for(
        self, supplier_ids: Sequence[UUID], per_supplier: int
    ) -> Mapping[UUID, tuple[OfferEvidence, ...]]: ...


class PurchaseHistory(Protocol):
    async def summarize(
        self, supplier_ids: Sequence[UUID], items: Sequence[QueryItem], records: int
    ) -> Mapping[UUID, PurchaseSummary]: ...


class ArchiveRosterReading(Protocol):
    async def roster(self, inns: Sequence[str]) -> ArchiveRoster | None: ...


class SearchArchive(Protocol):
    async def save(self, result: SearchResult) -> None: ...

    async def get(self, search_id: UUID) -> SearchResult | None: ...

    async def recent(self, limit: int) -> tuple[SearchSummary, ...]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new(self) -> UUID: ...
