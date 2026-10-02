from src.controller.analytics.dto import (
    AnalyticsFiltersDto,
    AnalyticsSourceDto,
    AnalyticsSourcesDto,
    AttentionDto,
    CategoriesDto,
    CategoryDto,
    CountDto,
    MetaDto,
    OverviewDto,
    PolicyDto,
    ProblemDto,
    QualityDto,
    RatioDto,
    RecordDto,
    RecordsDto,
    RunDto,
    RunsDto,
)
from src.models.analytics.measure import CountRow, Ratio
from src.models.analytics.records import RecordPage, RecordRow
from src.models.analytics.slice import CategoryRow, ProblemRow, RunRow, SourceRow
from src.models.analytics.view import AnalyticsView, AttentionItem
from src.models.enums import FetchStatus

OVERVIEW_CATEGORIES = 10
OVERVIEW_RUNS = 5


def ratio(value: Ratio) -> RatioDto:
    return RatioDto(
        numerator=value.numerator,
        denominator=value.denominator,
        unknown=value.unknown,
        share=value.share,
    )


def counts(rows: tuple[CountRow, ...]) -> list[CountDto]:
    return [CountDto(key=row.key, count=row.count) for row in rows]


def meta(view: AnalyticsView) -> MetaDto:
    snapshot = view.snapshot
    return MetaDto(
        snapshot_id=snapshot.snapshot_id,
        as_of=snapshot.as_of,
        computed_at=snapshot.computed_at,
        definitions_version=snapshot.definitions_version,
        delay_seconds=view.delay_seconds,
        warnings=list(view.warnings),
        filters=AnalyticsFiltersDto(
            source_id=snapshot.filters.source_id,
            source_type=snapshot.filters.source_type,
            region=snapshot.filters.region,
        ),
        policy=PolicyDto(
            offer_days=snapshot.policy.offer_days,
            registry_days=snapshot.policy.registry_days,
            period_days=snapshot.policy.period_days,
            version=snapshot.policy.version,
        ),
    )


def category(row: CategoryRow, name: str, total: int) -> CategoryDto:
    return CategoryDto(
        code=row.code,
        name=name,
        parent=row.parent,
        offers=row.offers,
        share=ratio(Ratio(row.offers, total)),
        companies=row.companies,
        verified_sellers=ratio(Ratio(row.verified_sellers, row.offers)),
        fresh=ratio(Ratio(row.fresh, row.offers)),
        priced=ratio(Ratio(row.priced, row.offers)),
        searchable=ratio(Ratio(row.searchable, row.offers)),
        system_assigned=row.system_assigned,
        source_reported=row.source_reported,
    )


def source_state(row: SourceRow) -> str:
    if row.last_attempt_at is None:
        return "never_run"
    if row.last_attempt_status == FetchStatus.FAILED:
        return "failed"
    if row.last_attempt_status == FetchStatus.PARTIAL:
        return "partial"
    return "ok"


def source(row: SourceRow) -> AnalyticsSourceDto:
    known = row.offers - row.unknown_age
    return AnalyticsSourceDto(
        source_id=row.source_id,
        name=row.name,
        provider_name=row.provider_name,
        source_type=row.source_type,
        state=source_state(row),
        offers=row.offers,
        companies=row.companies,
        fresh=ratio(Ratio(row.fresh, known, row.unknown_age)),
        last_seen_at=row.last_seen_at,
        last_success_at=row.last_success_at,
        last_attempt_at=row.last_attempt_at,
        last_attempt_status=row.last_attempt_status,
        runs=row.runs,
        failed_runs=row.failed_runs,
    )


def run(row: RunRow) -> RunDto:
    return RunDto(
        run_id=row.run_id,
        source_id=row.source_id,
        source_name=row.source_name,
        provider_name=row.provider_name,
        started_at=row.started_at,
        finished_at=row.finished_at,
        duration_seconds=max(0, int((row.finished_at - row.started_at).total_seconds())),
        status=row.status,
        suppliers_extracted=row.suppliers_extracted,
        offers_extracted=row.offers_extracted,
        error_message=row.error_message,
    )


def problem(row: ProblemRow) -> ProblemDto:
    return ProblemDto(
        source_id=row.source_id,
        name=row.name,
        offers=row.offers,
        no_supplier=row.no_supplier,
        unverified_seller=row.unverified_seller,
        no_category=row.no_category,
        no_price=row.no_price,
        no_attributes=row.no_attributes,
        stale=row.stale,
        unknown_age=row.unknown_age,
    )


def attention(item: AttentionItem) -> AttentionDto:
    return AttentionDto(
        code=item.code, source_id=item.source_id, count=item.count, total=item.total
    )


def categories_of(view: AnalyticsView) -> list[CategoryDto]:
    snapshot = view.snapshot
    return [
        category(row, view.names.get(row.code, ""), snapshot.offers) for row in snapshot.categories
    ]


def to_overview(view: AnalyticsView) -> OverviewDto:
    snapshot = view.snapshot
    top = [item for item in categories_of(view) if item.parent == ""][:OVERVIEW_CATEGORIES]
    return OverviewDto(
        meta=meta(view),
        offers=snapshot.offers,
        companies=snapshot.companies,
        composition=counts(snapshot.composition),
        fresh=ratio(snapshot.fresh),
        searchable=ratio(snapshot.searchable),
        runs_success=ratio(snapshot.runs_success),
        runs_partial=snapshot.runs_partial,
        attention=[attention(item) for item in view.attention],
        categories=top,
        sources=[source(row) for row in snapshot.sources],
        runs=[run(row) for row in snapshot.runs[:OVERVIEW_RUNS]],
    )


def to_categories(view: AnalyticsView) -> CategoriesDto:
    snapshot = view.snapshot
    return CategoriesDto(
        meta=meta(view),
        offers=snapshot.offers,
        items=categories_of(view),
        origins=counts(snapshot.origins),
    )


def to_quality(view: AnalyticsView) -> QualityDto:
    snapshot = view.snapshot
    return QualityDto(
        meta=meta(view),
        offers=snapshot.offers,
        fresh=ratio(snapshot.fresh),
        priced=ratio(snapshot.priced),
        age=counts(snapshot.age),
        availability=counts(snapshot.availability),
        problems=[problem(row) for row in snapshot.problems],
    )


def to_sources(view: AnalyticsView) -> AnalyticsSourcesDto:
    return AnalyticsSourcesDto(
        meta=meta(view), items=[source(row) for row in view.snapshot.sources]
    )


def to_runs(view: AnalyticsView) -> RunsDto:
    snapshot = view.snapshot
    return RunsDto(
        meta=meta(view),
        success=ratio(snapshot.runs_success),
        partial=snapshot.runs_partial,
        items=[run(row) for row in snapshot.runs],
    )


def record(row: RecordRow) -> RecordDto:
    return RecordDto(
        offer_id=row.offer_id,
        name=row.name,
        source_id=row.source_id,
        source_name=row.source_name,
        supplier_id=row.supplier_id,
        supplier_name=row.supplier_name,
        okpd2_code=row.okpd2_code,
        price=None if row.price is None else float(row.price),
        currency=row.currency,
        url=row.url,
        last_seen_at=row.last_seen_at,
        updated_at=row.updated_at,
    )


def to_records(page: RecordPage) -> RecordsDto:
    return RecordsDto(
        as_of=page.as_of,
        total=page.total,
        changed_after=page.changed_after,
        items=[record(row) for row in page.items],
    )
