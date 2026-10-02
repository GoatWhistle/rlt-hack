from typing import Protocol, runtime_checkable

from src.models.supplier_search import SupplierCandidate
from src.models.upload import Notice, Upload


class SearchEngine(Protocol):
    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]: ...


class UploadRepository(Protocol):
    async def save(self, upload: Upload) -> None: ...

    async def get(self, owner: str, upload_id: str) -> Upload | None: ...

    async def list(self, owner: str) -> list[Upload]: ...


@runtime_checkable
class CandidateEnrichment(Protocol):
    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]: ...


@runtime_checkable
class SearchVersion(Protocol):
    @property
    def version(self) -> str: ...


@runtime_checkable
class NoticeSearchEngine(Protocol):
    async def search_notice(self, notice: Notice, limit: int = 10) -> list[SupplierCandidate]: ...
