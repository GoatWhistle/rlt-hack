import asyncio
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from uuid import UUID

import pytest

from src.models.analytics.filters import AnalyticsFilters, FreshnessPolicy
from src.models.analytics.records import RecordPage, RecordQuery
from src.models.analytics.slice import AnalyticsSlice
from src.models.analytics.view import AttentionCode
from src.service.analytics.messages import safe_message
from src.service.analytics.service import AnalyticsService, AnalyticsSettings, snapshot_id_of
from src.service.errors import AnalyticsUnavailableError, StorageUnavailableError
from tests.fakes.analytics import MOMENT, RUN_ROW, SOURCE_ROW, make_slice


@dataclass
class MemoryStore:
    stored: dict[str, AnalyticsSlice] = field(default_factory=dict)
    published: list[AnalyticsSlice] = field(default_factory=list)

    async def latest(self, scope_key: str) -> AnalyticsSlice | None:
        return self.stored.get(scope_key)

    async def publish(self, snapshot: AnalyticsSlice) -> None:
        self.published.append(snapshot)
        self.stored[snapshot.filters.scope_key] = snapshot


@dataclass
class ScriptedBuilder:
    error: Exception | None = None
    delay: float = 0
    calls: int = 0
    template: AnalyticsSlice = field(default_factory=make_slice)

    async def build(
        self,
        snapshot_id: UUID,
        filters: AnalyticsFilters,
        policy: FreshnessPolicy,
        as_of: datetime,
        computed_at: datetime,
    ) -> AnalyticsSlice:
        self.calls += 1
        await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return replace(
            self.template,
            snapshot_id=snapshot_id,
            filters=filters,
            as_of=as_of,
            computed_at=computed_at,
        )


class Names:
    def name_of(self, code: str) -> str:
        return f"name {code}"


class Reader:
    async def page(
        self,
        filters: AnalyticsFilters,
        query: RecordQuery,
        policy: FreshnessPolicy,
        as_of: datetime,
    ) -> RecordPage:
        return RecordPage(as_of=as_of, total=0, items=(), changed_after=0)


class Clock:
    def __init__(self) -> None:
        self.moment = MOMENT

    def now(self) -> datetime:
        return self.moment


def service_of(
    store: MemoryStore,
    builder: ScriptedBuilder,
    clock: Clock,
    settings: AnalyticsSettings | None = None,
) -> AnalyticsService:
    return AnalyticsService(
        store, builder, Reader(), Names(), clock, settings or AnalyticsSettings(run_details=True)
    )


async def test_missing_snapshot_is_computed_and_published_once() -> None:
    store, builder, clock = MemoryStore(), ScriptedBuilder(), Clock()
    service = service_of(store, builder, clock)
    view = await service.view(AnalyticsFilters())
    assert len(store.published) == 1
    assert view.delay_seconds == 0
    assert view.names["01"] == "name 01"
    assert view.attention[0].code == AttentionCode.SOURCE_FAILED


async def test_fresh_snapshot_is_served_without_recomputing() -> None:
    store, builder, clock = MemoryStore(), ScriptedBuilder(), Clock()
    store.stored["all"] = make_slice()
    clock.moment = MOMENT + timedelta(seconds=60)
    view = await service_of(store, builder, clock).view(AnalyticsFilters())
    assert builder.calls == 0
    assert view.delay_seconds == 60
    assert view.warnings == ()


async def test_expired_snapshot_is_recomputed_and_concurrent_readers_share_one_run() -> None:
    store, builder, clock = MemoryStore(), ScriptedBuilder(delay=0.01), Clock()
    store.stored["all"] = make_slice()
    clock.moment = MOMENT + timedelta(hours=1)
    service = service_of(store, builder, clock)
    await asyncio.gather(*(service.view(AnalyticsFilters()) for _ in range(5)))
    assert builder.calls == 1


@pytest.mark.parametrize("error", [StorageUnavailableError(), TimeoutError()])
async def test_failed_refresh_keeps_previous_snapshot_with_warning(error: Exception) -> None:
    store, builder, clock = MemoryStore(), ScriptedBuilder(error=error), Clock()
    store.stored["all"] = make_slice()
    clock.moment = MOMENT + timedelta(hours=1)
    view = await service_of(store, builder, clock).view(AnalyticsFilters())
    assert view.warnings == ("refresh_failed",)
    assert view.snapshot.computed_at == MOMENT
    assert store.published == []


async def test_failed_refresh_without_previous_snapshot_is_unavailable() -> None:
    builder = ScriptedBuilder(error=StorageUnavailableError())
    service = service_of(MemoryStore(), builder, Clock())
    with pytest.raises(AnalyticsUnavailableError):
        await service.view(AnalyticsFilters())


async def test_computation_over_budget_falls_back_to_previous_snapshot() -> None:
    store, builder, clock = MemoryStore(), ScriptedBuilder(delay=1), Clock()
    store.stored["all"] = make_slice()
    clock.moment = MOMENT + timedelta(hours=1)
    settings = AnalyticsSettings(budget_seconds=0.01)
    view = await service_of(store, builder, clock, settings).view(AnalyticsFilters())
    assert view.warnings == ("refresh_failed",)


async def test_run_errors_are_cleaned_before_publication_and_hidden_by_default() -> None:
    dirty = replace(RUN_ROW, error_message="fail token=abc https://u:p@h.ru/x?key=1")
    template = replace(make_slice(), runs=(dirty,))
    store, builder, clock = MemoryStore(), ScriptedBuilder(template=template), Clock()
    shown = await service_of(store, builder, clock).view(AnalyticsFilters())
    assert store.published[0].runs[0].error_message == "fail token=*** https://***@h.ru/x"
    assert shown.snapshot.runs[0].error_message == store.published[0].runs[0].error_message
    hidden_store = MemoryStore(stored={"all": store.published[0]})
    hidden = await service_of(hidden_store, builder, clock, AnalyticsSettings()).view(
        AnalyticsFilters()
    )
    assert hidden.snapshot.runs[0].error_message == ""


async def test_republishing_the_same_moment_keeps_one_snapshot_id() -> None:
    filters = AnalyticsFilters(source_id=SOURCE_ROW.source_id)
    first = snapshot_id_of(filters, MOMENT.isoformat())
    assert first == snapshot_id_of(filters, MOMENT.isoformat())
    assert first != snapshot_id_of(AnalyticsFilters(), MOMENT.isoformat())
    assert first != snapshot_id_of(filters, (MOMENT + timedelta(seconds=1)).isoformat())


async def test_records_use_the_snapshot_boundary() -> None:
    service = service_of(MemoryStore(), ScriptedBuilder(), Clock())
    page = await service.records(AnalyticsFilters(), RecordQuery())
    assert page.as_of == MOMENT


def test_messages_hide_secrets_and_limit_length() -> None:
    assert safe_message("proxy=http://a:b@x.ru:80 down") == "proxy=*** down"
    assert safe_message("mail me@ex.org now") == "mail *** now"
    assert safe_message("x" * 1000).endswith("…")
    assert len(safe_message("x" * 1000)) == 240
    assert safe_message("") == ""


def test_scope_key_names_every_filter_and_stays_stable() -> None:
    assert AnalyticsFilters().scope_key == "all"
    assert AnalyticsFilters(region="78").scope_key == "region=78"
