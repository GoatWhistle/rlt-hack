from typing import Protocol

from src.models.supplier_search import SupplierCandidate


class QueryEncoder(Protocol):
    async def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]: ...


class SupplierIndex(Protocol):
    dimensions: int
    instruction: str

    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]: ...

    async def search(
        self, text: str, vector: list[float], limit: int
    ) -> list[SupplierCandidate]: ...
