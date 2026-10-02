from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.models.analytics.filters import (
    DEFINITIONS_VERSION,
    AnalyticsFilters,
    FreshnessPolicy,
)
from src.models.analytics.measure import CountRow, Ratio
from src.models.analytics.records import RecordPage, RecordQuery, RecordRow
from src.models.analytics.slice import (
    AnalyticsSlice,
    CategoryRow,
    ProblemRow,
    RunRow,
    SourceRow,
)
from src.models.analytics.view import AnalyticsView, AttentionCode, AttentionItem
from src.models.enums import FetchStatus, SourceType
from tests.fakes.domain import make_source, uid

MOMENT = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)
SOURCE = make_source()
CATEGORIES = (
    CategoryRow("01", "", 6, 3, 5, 4, 4, 5, 5, 1),
    CategoryRow("01.11", "01", 4, 2, 3, 3, 3, 3, 4, 0),
    CategoryRow("", "", 4, 1, 0, 2, 1, 2, 0, 0),
)
SOURCE_ROW = SourceRow(
    SOURCE.source_id,
    SOURCE.name,
    SOURCE.provider_name,
    SourceType.DIRECTORY,
    8,
    3,
    5,
    1,
    MOMENT,
    MOMENT,
    MOMENT,
    FetchStatus.FAILED,
    2,
    1,
)
RUN_ROW = RunRow(
    uid("run"),
    SOURCE.source_id,
    SOURCE.name,
    SOURCE.provider_name,
    MOMENT,
    MOMENT,
    FetchStatus.FAILED,
    2,
    4,
    "boom",
)


def make_slice(
    filters: AnalyticsFilters | None = None, computed_at: datetime = MOMENT
) -> AnalyticsSlice:
    return AnalyticsSlice(
        snapshot_id=uid("snapshot"),
        as_of=computed_at,
        computed_at=computed_at,
        definitions_version=DEFINITIONS_VERSION,
        filters=filters or AnalyticsFilters(),
        policy=FreshnessPolicy(),
        offers=10,
        companies=4,
        composition=(CountRow("directory", 8), CountRow("registry", 2)),
        fresh=Ratio(6, 9, 1),
        searchable=Ratio(7, 10),
        priced=Ratio(5, 8),
        runs_success=Ratio(1, 2),
        runs_partial=1,
        age=(CountRow("d1", 3), CountRow("unknown", 1)),
        availability=(CountRow("available", 6), CountRow("unknown", 4)),
        origins=(CountRow("system", 6), CountRow("absent", 4)),
        categories=CATEGORIES,
        sources=(SOURCE_ROW,),
        runs=(RUN_ROW,),
        problems=(ProblemRow(SOURCE.source_id, SOURCE.name, 8, 1, 1, 4, 3, 2, 5, 1),),
    )


def make_view(
    snapshot: AnalyticsSlice | None = None, warnings: tuple[str, ...] = ()
) -> AnalyticsView:
    return AnalyticsView(
        snapshot=snapshot or make_slice(),
        delay_seconds=12,
        warnings=warnings,
        attention=(AttentionItem(AttentionCode.SOURCE_FAILED, SOURCE.source_id, 1, 1),),
        names={"01": "Продукция сельского хозяйства"},
    )


def make_record() -> RecordRow:
    return RecordRow(
        offer_id=uid("offer:record"),
        name="Крупа",
        source_id=SOURCE.source_id,
        source_name=SOURCE.name,
        supplier_id=None,
        supplier_name="",
        okpd2_code="01.11.1",
        price=None,
        currency="RUB",
        url="https://catalog.example.org/1",
        last_seen_at=MOMENT,
        updated_at=MOMENT,
    )


@dataclass
class FakeCatalogAnalytics:
    view_value: AnalyticsView = field(default_factory=make_view)
    error: Exception | None = None
    scopes: list[AnalyticsFilters] = field(default_factory=list)
    queries: list[RecordQuery] = field(default_factory=list)

    async def view(self, filters: AnalyticsFilters) -> AnalyticsView:
        self.scopes.append(filters)
        if self.error is not None:
            raise self.error
        return self.view_value

    async def records(self, filters: AnalyticsFilters, query: RecordQuery) -> RecordPage:
        self.scopes.append(filters)
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return RecordPage(as_of=MOMENT, total=1, items=(make_record(),), changed_after=0)
