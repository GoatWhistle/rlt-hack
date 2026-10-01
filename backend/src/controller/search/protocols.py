from typing import Protocol

from src.models.supplier_search import SupplierCandidate


class SearchEngine(Protocol):
    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]: ...
