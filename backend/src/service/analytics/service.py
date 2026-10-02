import asyncio
import logging
from dataclasses import dataclass, field, replace
from uuid import NAMESPACE_URL, UUID, uuid5

from src.models.analytics.filters import DEFINITIONS_VERSION, AnalyticsFilters, FreshnessPolicy
from src.models.analytics.records import RecordPage, RecordQuery
from src.models.analytics.slice import AnalyticsSlice, RunRow
from src.models.analytics.view import AnalyticsView
from src.service.analytics.attention import attention_items
from src.service.analytics.messages import safe_message
from src.service.analytics.protocols import (
    CategoryNames,
    Clock,
    RecordReader,
    SliceBuilder,
    SliceStore,
)
from src.service.errors import AnalyticsUnavailableError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AnalyticsSettings:
    ttl_seconds: float = 900.0
    budget_seconds: float = 30.0
    run_details: bool = False
    policy: FreshnessPolicy = field(default_factory=FreshnessPolicy)


class AnalyticsService:
    """Отдаёт опубликованный срез; пересчитывает его, когда он устарел.

    Ошибка расчёта не стирает предыдущий срез: он показывается с предупреждением.
    """

    def __init__(
        self,
        store: SliceStore,
        builder: SliceBuilder,
        records: RecordReader,
        names: CategoryNames,
        clock: Clock,
        settings: AnalyticsSettings | None = None,
    ) -> None:
        self._store = store
        self._builder = builder
        self._records = records
        self._names = names
        self._clock = clock
        self._settings = settings or AnalyticsSettings()
        self._locks: dict[str, asyncio.Lock] = {}

    async def view(self, filters: AnalyticsFilters) -> AnalyticsView:
        key = filters.scope_key
        stored = await self._store.latest(key)
        if stored is not None and self._age(stored) < self._settings.ttl_seconds:
            return self._present(stored, ())
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            stored = await self._store.latest(key)
            if stored is not None and self._age(stored) < self._settings.ttl_seconds:
                return self._present(stored, ())
            try:
                return self._present(await self._compute(filters), ())
            except Exception:
                logger.exception("Срез аналитики %s не рассчитан", key)
                if stored is None:
                    raise AnalyticsUnavailableError("analytics snapshot is not available") from None
                return self._present(stored, ("refresh_failed",))

    async def refresh(self, filters: AnalyticsFilters) -> AnalyticsSlice:
        return await self._compute(filters)

    async def run_forever(self, filters: AnalyticsFilters, interval_seconds: float) -> None:
        while True:
            try:
                await self.refresh(filters)
            except asyncio.CancelledError:
                logger.info("Пересчёт аналитики остановлен")
                raise
            except Exception:
                logger.exception("Пересчёт аналитики не удался")
            await asyncio.sleep(interval_seconds)

    async def records(self, filters: AnalyticsFilters, query: RecordQuery) -> RecordPage:
        snapshot = (await self.view(filters)).snapshot
        return await self._records.page(filters, query, self._settings.policy, snapshot.as_of)

    async def _compute(self, filters: AnalyticsFilters) -> AnalyticsSlice:
        computed_at = self._clock.now()
        as_of = computed_at.replace(microsecond=0)
        async with asyncio.timeout(self._settings.budget_seconds):
            built = await self._builder.build(
                snapshot_id_of(filters, as_of.isoformat()),
                filters,
                self._settings.policy,
                as_of,
                computed_at,
            )
        cleaned = replace(
            built,
            runs=tuple(
                replace(run, error_message=safe_message(run.error_message)) for run in built.runs
            ),
        )
        await self._store.publish(cleaned)
        return cleaned

    def _age(self, snapshot: AnalyticsSlice) -> float:
        return (self._clock.now() - snapshot.computed_at).total_seconds()

    def _present(self, snapshot: AnalyticsSlice, warnings: tuple[str, ...]) -> AnalyticsView:
        delay = max(0, int(self._age(snapshot)))
        visible = replace(snapshot, runs=tuple(self._visible(run) for run in snapshot.runs))
        return AnalyticsView(
            snapshot=visible,
            delay_seconds=delay,
            warnings=warnings,
            attention=attention_items(snapshot),
            names={row.code: self._names.name_of(row.code) for row in snapshot.categories},
        )

    def _visible(self, run: RunRow) -> RunRow:
        return run if self._settings.run_details else replace(run, error_message="")


def snapshot_id_of(filters: AnalyticsFilters, as_of: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"analytics|{DEFINITIONS_VERSION}|{filters.scope_key}|{as_of}")
