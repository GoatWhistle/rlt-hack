from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from src.models.enums import CompanyRole, ComponentState
from src.models.health import ComponentHealth, Readiness
from src.models.search import SearchQuery
from src.models.search_result import SearchResult, SearchSummary
from src.models.supplier_profile import SupplierProfile
from src.models.upload import LotDetail, UploadDetail, UploadResults, UploadSummary
from src.service.errors import (
    LotNotFoundError,
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
        return self.summaries


@dataclass
class FakeSupplierProfiles:
    profile: SupplierProfile = field(default_factory=make_profile)

    async def get(self, supplier_id: UUID) -> SupplierProfile:
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
    started: int = 0
    stopped: int = 0

    async def start(self) -> None:
        self.started += 1

    async def stop(self) -> None:
        self.stopped += 1

    async def upload(self, file_name: str, content: bytes) -> UploadSummary:
        self.received.append((file_name, content))
        if self.error is not None:
            raise self.error
        return make_summary()

    async def recent(self, limit: int) -> tuple[UploadSummary, ...]:
        return (self.detail.summary,)[:limit]

    async def get(self, upload_id: UUID) -> UploadDetail:
        self._known(upload_id)
        return self.detail

    async def lot(self, upload_id: UUID, lot_id: str) -> LotDetail:
        self._known(upload_id)
        if lot_id != self.lot_detail.progress.lot.lot_id:
            raise LotNotFoundError(upload_id, lot_id)
        return self.lot_detail

    async def results(self, upload_id: UUID, lot_ids: Sequence[str]) -> UploadResults:
        self._known(upload_id)
        self.selections.append(tuple(lot_ids))
        return UploadResults(self.detail.summary, (make_processed(),))

    def _known(self, upload_id: UUID) -> None:
        if upload_id != UPLOAD_ID:
            raise UploadNotFoundError(upload_id)


@dataclass
class FakeReadiness:
    states: dict[str, ComponentState] = field(
        default_factory=lambda: {"clickhouse": ComponentState.UP}
    )

    async def readiness(self) -> Readiness:
        return Readiness(
            components=tuple(ComponentHealth(name, state) for name, state in self.states.items())
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

    async def aclose(self) -> None:
        self.closed += 1
