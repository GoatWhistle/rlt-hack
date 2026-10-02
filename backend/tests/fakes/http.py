from dataclasses import dataclass, field, replace
from uuid import UUID

from src.controller.http.protocols import BackgroundTask
from src.models.company.supplier_profile import SupplierProfile
from src.models.enums import CompanyRole, ComponentState
from src.models.operations.health import ComponentHealth, Readiness
from src.models.search.search import SearchQuery
from src.models.search.search_result import SearchHistory, SearchResult, SearchSummary
from src.service.errors import SearchNotFoundError, SupplierNotFoundError
from tests.fakes.analytics import FakeCatalogAnalytics
from tests.fakes.domain import (
    make_candidate,
    make_evidence,
    make_offer,
    make_offer_evidence,
    make_result,
    make_supplier,
)


def make_profile() -> SupplierProfile:
    supplier = make_supplier()
    return SupplierProfile(
        supplier=supplier,
        role=CompanyRole.DISTRIBUTOR,
        offers=(
            make_offer_evidence(
                replace(
                    make_offer(supplier=supplier),
                    brand="Увелка",
                    attributes={"Фасовка": "50 кг", "sku_id": "4607"},
                )
            ),
        ),
        role_evidence=make_evidence(),
    )


@dataclass
class FakeSupplierSearching:
    result: SearchResult = field(default_factory=lambda: make_result(make_candidate()))
    summaries: tuple[SearchSummary, ...] = ()
    error: Exception | None = None
    queries: list[SearchQuery] = field(default_factory=list)
    limits: list[int] = field(default_factory=list)
    cursors: list[UUID | None] = field(default_factory=list)

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

    async def recent(self, limit: int, before: UUID | None = None) -> SearchHistory:
        self.limits.append(limit)
        self.cursors.append(before)
        if self.error is not None:
            raise self.error
        return SearchHistory(
            searches=self.summaries[:limit],
            has_more=len(self.summaries) > limit,
            total=len(self.summaries),
        )


@dataclass
class FakeSupplierProfiles:
    profile: SupplierProfile = field(default_factory=make_profile)
    error: Exception | None = None

    async def get(self, supplier_id: UUID) -> SupplierProfile:
        if self.error is not None:
            raise self.error
        if supplier_id != self.profile.supplier.supplier_id:
            raise SupplierNotFoundError(supplier_id)
        return self.profile


@dataclass
class FakeBackgroundTask:
    started: int = 0
    stopped: int = 0

    async def start(self) -> None:
        self.started += 1

    async def stop(self) -> None:
        self.stopped += 1


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
    task: FakeBackgroundTask = field(default_factory=FakeBackgroundTask)
    readiness: FakeReadiness = field(default_factory=FakeReadiness)
    catalog: FakeCatalogAnalytics = field(default_factory=FakeCatalogAnalytics)
    closed: int = 0

    async def supplier_search(self) -> FakeSupplierSearching:
        return self.searching

    async def supplier_profiles(self) -> FakeSupplierProfiles:
        return self.profiles

    async def health(self) -> FakeReadiness:
        return self.readiness

    async def analytics(self) -> FakeCatalogAnalytics:
        return self.catalog

    async def background(self) -> tuple[BackgroundTask, ...]:
        return (self.task,)

    async def aclose(self) -> None:
        self.closed += 1
