from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.adapter.repository.clickhouse.analytics.builder import ClickHouseSliceBuilder
from src.adapter.repository.clickhouse.analytics.records import ClickHouseRecordReader
from src.adapter.repository.clickhouse.analytics.store import ClickHouseSliceStore
from src.adapter.repository.clickhouse.journal import ClickHouseJournalRepository
from src.models.analytics.filters import AnalyticsFilters, FreshnessPolicy
from src.models.analytics.records import RecordProblem, RecordQuery
from src.models.analytics.slice import AnalyticsSlice
from src.models.classification import Classification
from src.models.enums import (
    Availability,
    ClassificationMethod,
    FetchStatus,
    SourceType,
    VerificationStatus,
)
from src.models.journal import CrawlRun
from src.models.offer import Offer
from tests.adapter.repository.seed import Seeder
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.fakes.domain import CHECKED, make_offer, make_source, make_supplier, uid

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb

AS_OF = CHECKED + timedelta(days=2)
POLICY = FreshnessPolicy()
ALPHA = make_supplier("alpha", inn="7801234564")
BETA = make_supplier("beta", inn="780123456724")
CATALOG = make_source("catalog")
REGISTRY = make_source("registry", SourceType.REGISTRY)
EMPTY = make_source("empty")


def classified(
    offer: Offer, code: str, method: ClassificationMethod = ClassificationMethod.LEXICON
) -> Offer:
    return replace(offer, classification=Classification(okpd2_code=code, method=method))


async def seed_offers(seeder: Seeder) -> None:
    fresh = classified(make_offer("fresh", supplier=ALPHA), "01.11.1")
    old = replace(
        classified(make_offer("old", supplier=ALPHA), "01.11.2"),
        last_seen_at=CHECKED - timedelta(days=20),
        first_seen_at=CHECKED - timedelta(days=20),
    )
    bare = replace(make_offer("bare", supplier=BETA, price=None), supplier_id=None)
    bare = replace(bare, seller_status=VerificationStatus.UNVERIFIED)
    gone = classified(
        make_offer("gone", supplier=BETA, availability=Availability.UNAVAILABLE), "10.39.1"
    )
    listed = replace(
        classified(make_offer("listed", supplier=BETA), "01.13.1", ClassificationMethod.NONE),
        source_id=REGISTRY.source_id,
        last_seen_at=CHECKED - timedelta(days=10),
        first_seen_at=CHECKED - timedelta(days=10),
    )
    await seeder.offers(fresh, old, bare, gone, listed)


async def seed_runs(gateway: ChdbGateway) -> None:
    journal = ClickHouseJournalRepository(gateway)
    for name, finished, status, source in (
        ("a", CHECKED, FetchStatus.SUCCESS, CATALOG),
        ("b", CHECKED + timedelta(hours=1), FetchStatus.FAILED, CATALOG),
        ("c", CHECKED, FetchStatus.PARTIAL, REGISTRY),
    ):
        await journal.save_run(
            CrawlRun(
                run_id=uid(f"run:{name}"),
                source_id=source.source_id,
                started_at=finished - timedelta(minutes=5),
                finished_at=finished,
                status=status,
                suppliers_extracted=2,
                offers_extracted=4,
                provider_name=source.provider_name,
                error_message="token=abc boom" if status == FetchStatus.FAILED else "",
            )
        )


async def seeded(gateway: ChdbGateway) -> None:
    seeder = Seeder(gateway)
    await seeder.suppliers(ALPHA, BETA)
    await seeder.sources(CATALOG, REGISTRY, EMPTY)
    await seed_offers(seeder)
    await seed_runs(gateway)


async def build(gateway: ChdbGateway, filters: AnalyticsFilters | None = None) -> AnalyticsSlice:
    return await ClickHouseSliceBuilder(gateway).build(
        uuid4(), filters or AnalyticsFilters(), POLICY, AS_OF, AS_OF
    )


async def test_totals_and_ratios_count_against_documented_bases(gateway: ChdbGateway) -> None:
    await seeded(gateway)
    result = await build(gateway)
    assert result.offers == 5
    assert result.companies == 2
    assert {row.key: row.count for row in result.composition} == {"directory": 4, "registry": 1}
    assert (result.fresh.numerator, result.fresh.denominator, result.fresh.unknown) == (4, 5, 0)
    assert result.searchable.numerator == 3
    assert (result.priced.numerator, result.priced.denominator) == (3, 4)
    assert {row.key: row.count for row in result.origins} == {
        "system": 3,
        "source": 1,
        "absent": 1,
    }
    assert {row.key: row.count for row in result.age} == {"d7": 3, "d30": 2}


async def test_categories_nest_groups_under_classes_and_keep_uncategorized(
    gateway: ChdbGateway,
) -> None:
    await seeded(gateway)
    rows = {row.code: row for row in (await build(gateway)).categories}
    assert (rows["01"].offers, rows["01"].parent) == (3, "")
    assert (rows["01.11"].offers, rows["01.11"].parent) == (2, "01")
    assert rows[""].offers == 1
    assert rows["01"].companies == 2


async def test_sources_keep_never_run_and_failed_states_apart(gateway: ChdbGateway) -> None:
    await seeded(gateway)
    sources = {row.provider_name: row for row in (await build(gateway)).sources}
    assert sources["catalog"].last_attempt_status == FetchStatus.FAILED
    assert sources["catalog"].last_success_at is not None
    assert sources["catalog"].failed_runs == 1
    assert sources["empty"].last_attempt_at is None
    assert sources["empty"].offers == 0
    assert sources["registry"].last_attempt_status == FetchStatus.PARTIAL


async def test_runs_ratio_counts_only_completed_runs_of_the_period(gateway: ChdbGateway) -> None:
    await seeded(gateway)
    result = await build(gateway)
    assert (result.runs_success.numerator, result.runs_success.denominator) == (1, 3)
    assert result.runs_partial == 1
    assert result.runs[0].status == FetchStatus.FAILED


async def test_filters_apply_to_every_panel(gateway: ChdbGateway) -> None:
    await seeded(gateway)
    result = await build(gateway, AnalyticsFilters(source_type=SourceType.REGISTRY))
    assert result.offers == 1
    assert [row.provider_name for row in result.sources] == ["registry"]
    assert [row.provider_name for row in result.runs] == ["registry"]
    empty = await build(gateway, AnalyticsFilters(region="99"))
    assert empty.offers == 0
    assert empty.fresh.share is None


async def test_problem_matrix_matches_record_lists(gateway: ChdbGateway) -> None:
    await seeded(gateway)
    result = await build(gateway)
    catalog = next(row for row in result.problems if row.source_id == CATALOG.source_id)
    assert (catalog.no_supplier, catalog.no_price, catalog.stale) == (1, 1, 1)
    reader = ClickHouseRecordReader(gateway)
    page = await reader.page(
        AnalyticsFilters(), RecordQuery(problem=RecordProblem.STALE), POLICY, AS_OF
    )
    assert page.total == catalog.stale + 0
    assert [item.name for item in page.items] == ["Товар old"]


async def test_records_filter_by_category_prefix_and_report_changes_after_snapshot(
    gateway: ChdbGateway,
) -> None:
    await seeded(gateway)
    reader = ClickHouseRecordReader(gateway)
    page = await reader.page(AnalyticsFilters(), RecordQuery(category="01.11"), POLICY, AS_OF)
    assert page.total == 2
    assert page.items[0].price == Decimal("84.50")
    early = await reader.page(
        AnalyticsFilters(), RecordQuery(), POLICY, CHECKED - timedelta(days=1)
    )
    assert early.changed_after == early.total


async def test_store_round_trips_and_republish_keeps_one_snapshot(gateway: ChdbGateway) -> None:
    await seeded(gateway)
    snapshot = await build(gateway)
    store = ClickHouseSliceStore(gateway)
    assert await store.latest("all") is None
    await store.publish(snapshot)
    await store.publish(snapshot)
    assert await store.latest("all") == snapshot
    assert await store.latest("source=nothing") is None
