"""Сборка зависимостей: единственное место, где слои соединяются.

Здесь объявляются источники и подключаются их адаптеры: каждый включается своим
флагом конфигурации. Добавление источника — новый адаптер в
`src/adapter/supplier/` и ветка с его флагом в `providers`; сервис, хранилище и
схема при этом не меняются.

Контейнер создаётся на процесс и живёт весь запуск: соединение с ClickHouse
делят все конкурентные обходы. Для будущего HTTP API он создаётся один раз.
"""

from types import TracebackType

from src.adapter.clock import SystemClock
from src.adapter.repository.clickhouse.client import create_client
from src.adapter.repository.clickhouse.gateway import ConnectGateway
from src.adapter.repository.clickhouse.journal import ClickHouseJournalRepository
from src.adapter.repository.clickhouse.migrator import Migrator
from src.adapter.repository.clickhouse.offer import ClickHouseOfferRepository
from src.adapter.repository.clickhouse.package import ClickHousePackageRepository
from src.adapter.repository.clickhouse.source import ClickHouseSourceRepository
from src.adapter.repository.clickhouse.supplier import ClickHouseSupplierRepository
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.adapter.supplier import identity
from src.adapter.supplier.aboutpartner_web import PROVIDER_NAME as ABOUTPARTNER
from src.adapter.supplier.aboutpartner_web import AboutPartnerWebProvider
from src.adapter.supplier.optkatalog_web import PROVIDER_NAME as OPTKATALOG
from src.adapter.supplier.optkatalog_web import OptKatalogWebProvider
from src.adapter.supplier.productcenter_web import PROVIDER_NAME as PRODUCTCENTER
from src.adapter.supplier.productcenter_web import ProductCenterWebProvider
from src.adapter.supplier.schema_org_web import PROVIDER_NAME as SCHEMA_ORG
from src.adapter.supplier.schema_org_web import SchemaOrgWebProvider
from src.adapter.supplier.supplier_dataset import PROVIDER_NAME as SUPPLIER_DATASET
from src.adapter.supplier.supplier_dataset import SupplierDatasetProvider
from src.adapter.supplier.texzakaz_web import PROVIDER_NAME as TEXZAKAZ
from src.adapter.supplier.texzakaz_web import TexZakazWebProvider
from src.adapter.supplier.yml_feed import PROVIDER_NAME as YML_FEED
from src.adapter.supplier.yml_feed import YmlFeedProvider
from src.application.config import AppConfig
from src.models.enums import SourceType
from src.models.source import Source
from src.service.supplier.protocols import SupplierProvider
from src.service.supplier.worker import SupplierSyncWorker


def _source(name: str, base_url: str, source_type: SourceType, provider_name: str) -> Source:
    return Source(
        source_id=identity.source_id(base_url, provider_name),
        name=name,
        base_url=base_url,
        source_type=source_type,
        provider_name=provider_name,
    )


class Container:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._versions = VersionSequencer()
        self._gateway: ConnectGateway | None = None

    @property
    def config(self) -> AppConfig:
        return self._config

    async def gateway(self) -> ConnectGateway:
        if self._gateway is None:
            self._gateway = ConnectGateway(await create_client(self._config.clickhouse))
        return self._gateway

    async def migrator(self) -> Migrator:
        return Migrator(await self.gateway(), database=self._config.clickhouse.database)

    async def sources(self) -> ClickHouseSourceRepository:
        return ClickHouseSourceRepository(
            await self.gateway(), self._versions, self._config.clickhouse.database
        )

    async def journal(self) -> ClickHouseJournalRepository:
        return ClickHouseJournalRepository(await self.gateway(), self._config.clickhouse.database)

    async def package_repository(self) -> ClickHousePackageRepository:
        database = self._config.clickhouse.database
        gateway = await self.gateway()
        return ClickHousePackageRepository(
            sources=await self.sources(),
            suppliers=ClickHouseSupplierRepository(gateway, self._versions, database),
            offers=ClickHouseOfferRepository(gateway, self._versions, database),
            batch_size=self._config.write_batch_size,
        )

    def providers(self) -> list[SupplierProvider]:
        """Адаптеры включённых источников в порядке объявления."""
        config = self._config
        providers: list[SupplierProvider] = []

        if config.use_supplier_dataset_provider:
            providers.append(
                SupplierDatasetProvider(
                    source_defaults=_source(
                        name="Поставщики из задания",
                        base_url=config.dataset_path.as_uri(),
                        source_type=SourceType.DATASET,
                        provider_name=SUPPLIER_DATASET,
                    ),
                    dataset_path=config.dataset_path,
                    region=config.dataset_region,
                )
            )

        if config.use_yml_feed_provider:
            for feed_url in config.feed_urls:
                providers.append(
                    YmlFeedProvider(
                        source_defaults=_source(
                            name=f"Фид {feed_url}",
                            base_url=feed_url,
                            source_type=SourceType.FEED,
                            provider_name=YML_FEED,
                        ),
                        feed_url=feed_url,
                        http_timeout=config.request_timeout,
                    )
                )

        if config.use_schema_org_provider:
            for site_url in config.site_urls:
                providers.append(
                    SchemaOrgWebProvider(
                        source_defaults=_source(
                            name=f"Сайт {site_url}",
                            base_url=site_url,
                            source_type=SourceType.WEBSITE,
                            provider_name=SCHEMA_ORG,
                        ),
                        max_pages=config.max_cards_per_source,
                        max_concurrent=config.parallel_requests,
                        http_timeout=config.request_timeout,
                    )
                )

        if config.use_optkatalog_provider:
            providers.append(
                OptKatalogWebProvider(
                    source_defaults=_source(
                        name="ОптКаталог",
                        base_url="https://optkatalog.ru/",
                        source_type=SourceType.DIRECTORY,
                        provider_name=OPTKATALOG,
                    ),
                    max_companies=config.max_cards_per_source,
                    max_concurrent=config.parallel_requests,
                    http_timeout=config.request_timeout,
                )
            )

        if config.use_aboutpartner_provider:
            providers.append(
                AboutPartnerWebProvider(
                    source_defaults=_source(
                        name="О Партнёре",
                        base_url="https://aboutpartner.ru/",
                        source_type=SourceType.DIRECTORY,
                        provider_name=ABOUTPARTNER,
                    ),
                    max_companies=config.max_cards_per_source,
                    max_concurrent=config.parallel_requests,
                    http_timeout=config.request_timeout,
                )
            )

        if config.use_texzakaz_provider:
            providers.append(
                TexZakazWebProvider(
                    source_defaults=_source(
                        name="ТехЗаказ",
                        base_url="https://texzakaz.ru/",
                        source_type=SourceType.DIRECTORY,
                        provider_name=TEXZAKAZ,
                    ),
                    max_companies=config.max_cards_per_source,
                    max_concurrent=config.parallel_requests,
                    http_timeout=config.request_timeout,
                )
            )

        if config.use_productcenter_provider:
            providers.append(
                ProductCenterWebProvider(
                    source_defaults=_source(
                        name="ПродуктЦентр",
                        base_url="https://productcenter.ru/",
                        source_type=SourceType.DIRECTORY,
                        provider_name=PRODUCTCENTER,
                    ),
                    max_concurrent=config.productcenter_parallel_requests,
                    http_timeout=config.request_timeout,
                    max_cards=config.productcenter_max_cards or None,
                    connection_retries=config.productcenter_connection_retries,
                    request_interval=config.productcenter_request_interval,
                    cache_dir=config.productcenter_cache_dir,
                )
            )

        return providers

    async def supplier_worker(self) -> SupplierSyncWorker:
        return SupplierSyncWorker(
            providers=self.providers(),
            storage=await self.package_repository(),
            journal=await self.journal(),
            clock=SystemClock(),
            interval_seconds=self._config.sync_interval_seconds,
            max_parallel_sources=self._config.parallel_sources,
        )

    async def aclose(self) -> None:
        if self._gateway is not None:
            await self._gateway.close()
            self._gateway = None

    async def __aenter__(self) -> "Container":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()
