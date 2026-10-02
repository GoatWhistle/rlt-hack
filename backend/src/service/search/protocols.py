from typing import Protocol, runtime_checkable

from src.models.search.search_context import SearchContext
from src.models.search.supplier_search import SupplierCandidate


class QueryEncoder(Protocol):
    async def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]: ...


class SupplierIndex(Protocol):
    dimensions: int
    instruction: str

    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]: ...

    async def search(
        self, text: str, vector: list[float], limit: int
    ) -> list[SupplierCandidate]: ...


@runtime_checkable
class IndexVersion(Protocol):
    @property
    def version(self) -> str: ...


@runtime_checkable
class ContextualSupplierIndex(Protocol):
    async def search_context(
        self, text: str, vector: list[float], limit: int, context: SearchContext
    ) -> list[SupplierCandidate]: ...
