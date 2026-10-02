from collections.abc import Mapping, Sequence
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.models.catalog.supplier import Supplier
from src.models.company.offer_evidence import OfferEvidence
from src.models.company.purchase import PurchaseSummary
from src.models.ranking.retrieval import RetrievalHits
from src.models.search.query_item import QueryItem, SearchRequest
from src.models.search.search import SearchQuery
from src.models.search.search_result import SearchResult, SearchSummary


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

    async def current_ids(
        self, supplier_ids: Sequence[UUID], per_supplier: int
    ) -> Mapping[UUID, tuple[UUID, ...]]: ...


class PurchaseHistory(Protocol):
    async def summarize(
        self, supplier_ids: Sequence[UUID], items: Sequence[QueryItem], records: int
    ) -> Mapping[UUID, PurchaseSummary]: ...


class SearchArchive(Protocol):
    async def save(self, result: SearchResult) -> None: ...

    async def get(self, search_id: UUID) -> SearchResult | None: ...

    async def recent(self, limit: int) -> tuple[SearchSummary, ...]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new(self) -> UUID: ...


class WorkShare(Protocol):
    def scope(self) -> AbstractAsyncContextManager[None]: ...


class StageTimer(Protocol):
    def stage(self, name: str) -> AbstractContextManager[None]: ...
