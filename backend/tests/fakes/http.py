from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from src.controller.http.protocols import BackgroundTask
from src.models.archive_purchase import ArchivePurchase
from src.models.enums import CompanyRole, ComponentState
from src.models.health import ComponentHealth, Readiness
from src.models.search import SearchQuery
from src.models.search_result import SearchResult, SearchSummary
from src.models.supplier_profile import SupplierProfile
from src.models.upload import LotDetail, UploadDetail, UploadResults, UploadSummary
from src.service.errors import (
    LotNotFoundError,
    PurchaseNotFoundError,
    SearchNotFoundError,
    SupplierNotFoundError,
    UploadNotFoundError,
)
from tests.fakes.domain import (
    make_candidate,
    make_evidence,
    make_offer,
    make_offer_evidence,
    make_result,
    make_supplier,
)
from tests.fakes.uploads import (
    UPLOAD_ID,
    make_detail,
    make_lot_detail,
    make_lot_result,
    make_processed,
    make_summary,
)


def make_profile() -> SupplierProfile:
    supplier = make_supplier()
    return SupplierProfile(
        supplier=supplier,
        role=CompanyRole.DISTRIBUTOR,
        offers=(make_offer_evidence(make_offer(supplier=supplier)),),
        role_evidence=make_evidence(),
    )


@dataclass
class FakeSupplierSearching:
    result: SearchResult = field(default_factory=lambda: make_result(make_candidate()))
    summaries: tuple[SearchSummary, ...] = ()
    error: Exception | None = None
    queries: list[SearchQuery] = field(default_factory=list)
    limits: list[int] = field(default_factory=list)

    async def search(self, query: SearchQuery) -> SearchResult:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return self.result

    async def get(self, search_id: UUID) -> SearchResult:
        if self.error is not None:
            raise self.error
        if search_id != self.result.search_id:
            raise SearchNotFoundError(search_id)
        return self.result

    async def recent(self, limit: int) -> tuple[SearchSummary, ...]:
        self.limits.append(limit)
        if self.error is not None:
            raise self.error
        return self.summaries


@dataclass
class FakeSupplierProfiles:
    profile: SupplierProfile = field(default_factory=make_profile)
    error: Exception | None = None
    purchases: dict[str, ArchivePurchase] = field(default_factory=dict)

    async def purchase(self, supplier_id: UUID, lot_id: str) -> ArchivePurchase:
        await self.get(supplier_id)
        found = self.purchases.get(lot_id)
        if found is None:
            raise PurchaseNotFoundError(lot_id)
        return found

    async def get(self, supplier_id: UUID) -> SupplierProfile:
        if self.error is not None:
            raise self.error
        if supplier_id != self.profile.supplier.supplier_id:
            raise SupplierNotFoundError(supplier_id)
        return self.profile


@dataclass
class FakeProcurementUploads:
    detail: UploadDetail = field(default_factory=lambda: make_detail(make_lot_result()))
    lot_detail: LotDetail = field(default_factory=lambda: make_lot_detail(make_lot_result()))
    error: Exception | None = None
    received: list[tuple[str, bytes]] = field(default_factory=list)
    selections: list[tuple[str, ...]] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)
    started: int = 0
    stopped: int = 0
    summaries: int = 0
    details: int = 0

    async def start(self) -> None:
        self.started += 1

    async def stop(self) -> None:
        self.stopped += 1

    async def upload(self, owner: str, file_name: str, content: bytes) -> UploadSummary:
        self.owners.append(owner)
        self.received.append((file_name, content))
        if self.error is not None:
            raise self.error
        return make_summary()

    async def recent(self, owner: str, limit: int) -> tuple[UploadSummary, ...]:
        self.owners.append(owner)
        if self.error is not None:
            raise self.error
        return (self.detail.summary,)[:limit]

    async def summary(self, owner: str, upload_id: UUID) -> UploadSummary:
        self._known(owner, upload_id)
        self.summaries += 1
        return self.detail.summary

    async def get(self, owner: str, upload_id: UUID) -> UploadDetail:
        self._known(owner, upload_id)
        self.details += 1
        return self.detail

    async def lot(self, owner: str, upload_id: UUID, lot_id: str) -> LotDetail:
        self._known(owner, upload_id)
        if lot_id != self.lot_detail.progress.lot.lot_id:
            raise LotNotFoundError(upload_id, lot_id)
        return self.lot_detail

    async def results(self, owner: str, upload_id: UUID, lot_ids: Sequence[str]) -> UploadResults:
        self._known(owner, upload_id)
        self.selections.append(tuple(lot_ids))
        return UploadResults(self.detail.summary, (make_processed(),))

    def _known(self, owner: str, upload_id: UUID) -> None:
        self.owners.append(owner)
        if self.error is not None:
            raise self.error
        if upload_id != UPLOAD_ID:
            raise UploadNotFoundError(upload_id)


@dataclass
class FakeReadiness:
    states: dict[str, ComponentState] = field(
        default_factory=lambda: {"clickhouse": ComponentState.UP}
    )
    optional: set[str] = field(default_factory=set)

    async def readiness(self) -> Readiness:
        return Readiness(
            components=tuple(
                ComponentHealth(name, state, name not in self.optional)
                for name, state in self.states.items()
            )
        )


@dataclass
class FakeServiceProvider:
    searching: FakeSupplierSearching = field(default_factory=FakeSupplierSearching)
    profiles: FakeSupplierProfiles = field(default_factory=FakeSupplierProfiles)
    uploads: FakeProcurementUploads = field(default_factory=FakeProcurementUploads)
    readiness: FakeReadiness = field(default_factory=FakeReadiness)
    closed: int = 0

    async def supplier_search(self) -> FakeSupplierSearching:
        return self.searching

    async def supplier_profiles(self) -> FakeSupplierProfiles:
        return self.profiles

    async def procurement_uploads(self) -> FakeProcurementUploads:
        return self.uploads

    async def health(self) -> FakeReadiness:
        return self.readiness

    async def background(self) -> tuple[BackgroundTask, ...]:
        return (self.uploads,)

    async def aclose(self) -> None:
        self.closed += 1
