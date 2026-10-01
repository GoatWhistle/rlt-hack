from typing import Protocol, runtime_checkable

from src.models.supplier_search import SupplierCandidate
from src.models.upload import Upload


class SearchEngine(Protocol):
    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]: ...


class UploadRepository(Protocol):
    async def save(self, upload: Upload) -> None: ...

    async def get(self, owner: str, upload_id: str) -> Upload | None: ...

    async def list(self, owner: str) -> list[Upload]: ...


@runtime_checkable
class CandidateEnrichment(Protocol):
    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]: ...
