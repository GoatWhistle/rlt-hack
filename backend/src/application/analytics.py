from src.adapter.repository.clickhouse.analytics.builder import ClickHouseSliceBuilder
from src.adapter.repository.clickhouse.analytics.records import ClickHouseRecordReader
from src.adapter.repository.clickhouse.analytics.store import ClickHouseSliceStore
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.reference import load_category_names
from src.adapter.system.clock import SystemClock
from src.application.config import AppConfig
from src.models.analytics.filters import FreshnessPolicy
from src.service.analytics.service import AnalyticsService, AnalyticsSettings


async def analytics_service(
    config: AppConfig, gateway: SqlGateway, writer: SqlGateway | None = None
) -> AnalyticsService:
    database = config.clickhouse.database
    options = config.analytics
    return AnalyticsService(
        store=ClickHouseSliceStore(gateway, database, writer),
        builder=ClickHouseSliceBuilder(gateway, database),
        records=ClickHouseRecordReader(gateway, database),
        names=await load_category_names(config.reference_dir),
        clock=SystemClock(),
        settings=AnalyticsSettings(
            ttl_seconds=options.ttl_seconds,
            budget_seconds=options.budget_seconds,
            run_details=options.run_details,
            policy=FreshnessPolicy(
                offer_days=options.offer_days,
                registry_days=options.registry_days,
                period_days=options.period_days,
            ),
        ),
    )
