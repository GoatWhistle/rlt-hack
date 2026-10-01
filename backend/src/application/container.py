"""Сборка зависимостей: единственное место, где слои соединяются.

Здесь объявляются источники и подключаются их адаптеры: каждый включается своим
флагом конфигурации. Добавление источника — новый адаптер в
`src/adapter/supplier/` и ветка с его флагом в `providers`; сервис, хранилище и
схема при этом не меняются.

Контейнер создаётся на процесс и живёт весь запуск: соединение с ClickHouse
делят все конкурентные обходы. Для будущего HTTP API он создаётся один раз.
"""

from types import TracebackType

from src.adapter.repository.clickhouse.archive import ClickHouseArchiveRepository
from src.adapter.repository.clickhouse.client import create_client
from src.adapter.repository.clickhouse.gateway import ConnectGateway
from src.adapter.repository.clickhouse.journal import ClickHouseJournalRepository
from src.adapter.repository.clickhouse.migrator import Migrator
from src.adapter.repository.clickhouse.offer import ClickHouseOfferRepository
from src.adapter.repository.clickhouse.package import ClickHousePackageRepository
from src.adapter.repository.clickhouse.pool.gateway import GatewayPool
from src.adapter.repository.clickhouse.source import ClickHouseSourceRepository
from src.adapter.repository.clickhouse.supplier import ClickHouseSupplierRepository
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.adapter.repository.reference import (
    load_classifier_reference,
    load_normalizer_reference,
)
from src.adapter.supplier import identity
from src.adapter.supplier.aboutpartner_web import PROVIDER_NAME as ABOUTPARTNER
from src.adapter.supplier.aboutpartner_web import AboutPartnerWebProvider
from src.adapter.supplier.gisp_registry import PROVIDER_NAME as GISP_REGISTRY
from src.adapter.supplier.gisp_registry import GispRegistryProvider
from src.adapter.supplier.moscow_suppliers import PROVIDER_NAME as MOSCOW_SUPPLIERS
from src.adapter.supplier.moscow_suppliers import MoscowSuppliersProvider
from src.adapter.supplier.offer_identity import OfferIdentityRules
from src.adapter.supplier.optkatalog_web import PROVIDER_NAME as OPTKATALOG
from src.adapter.supplier.optkatalog_web import OptKatalogWebProvider
from src.adapter.supplier.productcenter_web import PROVIDER_NAME as PRODUCTCENTER
from src.adapter.supplier.productcenter_web import ProductCenterWebProvider
from src.adapter.supplier.pulscen_web import PROVIDER_NAME as PULSCEN
from src.adapter.supplier.pulscen_web import PulscenSnapshotProvider, PulscenWebProvider
from src.adapter.supplier.pulscen_web.snapshot import PROVIDER_NAME as PULSCEN_SNAPSHOT
from src.adapter.supplier.schema_org_web import PROVIDER_NAME as SCHEMA_ORG
from src.adapter.supplier.schema_org_web import SchemaOrgWebProvider
from src.adapter.supplier.supplier_dataset import PROVIDER_NAME as SUPPLIER_DATASET
from src.adapter.supplier.supplier_dataset import SupplierDatasetProvider
from src.adapter.supplier.texzakaz_web import PROVIDER_NAME as TEXZAKAZ
from src.adapter.supplier.texzakaz_web import TexZakazWebProvider
from src.adapter.supplier.yml_feed import PROVIDER_NAME as YML_FEED
from src.adapter.supplier.yml_feed import YmlFeedProvider
from src.adapter.system.clock import SystemClock
from src.application.config import AppConfig
from src.models.enums import SourceType
from src.models.source import Source
from src.service.classifier import OfferClassifier
from src.service.normalizer import OfferNormalizer
from src.service.supplier.enrich import OfferEnrichmentService
from src.service.supplier.protocols import SupplierProvider
from src.service.supplier.reidentify import OfferReidentifyService
from src.service.supplier.worker import SupplierSyncWorker

JOB_POOL_SIZE = 1


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
        self._gateway: GatewayPool | None = None
        self._api_gateway: GatewayPool | None = None
        # Справочники читаются один раз на процесс: они не меняются на ходу.
        self._normalizer: OfferNormalizer | None = None
        self._classifier: OfferClassifier | None = None

    @property
    def config(self) -> AppConfig:
        return self._config

    async def gateway(self) -> GatewayPool:
        if self._gateway is None:
            self._gateway = GatewayPool(self._open_gateway, JOB_POOL_SIZE)
        return self._gateway

    async def api_gateway(self) -> GatewayPool:
        if self._api_gateway is None:
            self._api_gateway = GatewayPool(self._open_gateway, self._config.clickhouse.pool_size)
        return self._api_gateway

    async def _open_gateway(self) -> ConnectGateway:
        return ConnectGateway(await create_client(self._config.clickhouse))

    async def migrator(self) -> Migrator:
        return Migrator(await self.gateway(), database=self._config.clickhouse.database)

    async def sources(self) -> ClickHouseSourceRepository:
        return ClickHouseSourceRepository(
            await self.gateway(), self._versions, self._config.clickhouse.database
        )

    async def journal(self) -> ClickHouseJournalRepository:
        return ClickHouseJournalRepository(await self.gateway(), self._config.clickhouse.database)

    async def offers(self) -> ClickHouseOfferRepository:
        return ClickHouseOfferRepository(
            await self.gateway(), self._versions, self._config.clickhouse.database
        )

    async def package_repository(self) -> ClickHousePackageRepository:
        database = self._config.clickhouse.database
        gateway = await self.gateway()
        return ClickHousePackageRepository(
            sources=await self.sources(),
            suppliers=ClickHouseSupplierRepository(gateway, self._versions, database),
            offers=await self.offers(),
            batch_size=self._config.write_batch_size,
        )

    async def normalizer(self) -> OfferNormalizer:
        """Нормализатор знает только свои справочники и правила."""
        if self._normalizer is None:
            reference = await load_normalizer_reference(self._config.reference_dir)
            self._normalizer = OfferNormalizer(reference.units, reference.rules)
        return self._normalizer

    async def classifier(self) -> OfferClassifier:
        """Ключ сравнения названий берётся у нормализатора: он один на систему."""
        if self._classifier is None:
            normalizer = await self.normalizer()
            reference = await load_classifier_reference(
                normalizer.name_key, normalizer.name_stems, self._config.reference_dir
            )
            archive = None
            if self._config.use_archive_channel:
                archive = ClickHouseArchiveRepository(
                    await self.gateway(), self._config.clickhouse.database
                )
            self._classifier = OfferClassifier(
                okpd2=reference.okpd2,
                rubrics=reference.rubrics,
                lexicon=reference.lexicon,
                categories=reference.categories,
                archive=archive,
                archive_limit=self._config.archive_limit,
                name_key=normalizer.name_key,
            )
        return self._classifier

    async def enrichment(self) -> OfferEnrichmentService:
        return OfferEnrichmentService(
            sources=await self.sources(),
            offers=await self.offers(),
            normalizer=await self.normalizer(),
            classifier=await self.classifier(),
            clock=SystemClock(),
            batch_size=self._config.write_batch_size,
        )

    async def reidentify(self) -> OfferReidentifyService:
        """Перевод сохранённых позиций на действующее правило ключа."""
        return OfferReidentifyService(
            sources=await self.sources(),
            offers=await self.offers(),
            identity=OfferIdentityRules(),
            clock=SystemClock(),
            page_size=self._config.write_batch_size,
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

        if config.use_gisp_registry_provider:
            providers.append(
                GispRegistryProvider(
                    source_defaults=_source(
                        name="Реестр российской промышленной продукции ГИСП",
                        base_url="https://gisp.gov.ru/pp719v2/pub/prod/",
                        source_type=SourceType.REGISTRY,
                        provider_name=GISP_REGISTRY,
                    ),
                    export_location=config.gisp_export_location,
                    http_timeout=config.request_timeout,
                    max_concurrent=config.parallel_requests,
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

        if config.use_moscow_suppliers_provider:
            providers.append(
                MoscowSuppliersProvider(
                    source_defaults=_source(
                        name="Портал поставщиков Москвы",
                        base_url="https://zakupki.mos.ru/",
                        source_type=SourceType.DIRECTORY,
                        provider_name=MOSCOW_SUPPLIERS,
                    ),
                    export_url=config.moscow_suppliers_export_url,
                    http_timeout=config.request_timeout,
                )
            )

        if config.use_pulscen_provider:
            providers.append(
                PulscenWebProvider(
                    source_defaults=_source(
                        name="Пульс цен",
                        base_url="https://www.pulscen.ru/",
                        source_type=SourceType.DIRECTORY,
                        provider_name=PULSCEN,
                    ),
                    delay_seconds=config.pulscen_delay_seconds,
                    http_timeout=config.request_timeout,
                )
            )

        if config.pulscen_snapshot_path is not None:
            providers.append(
                PulscenSnapshotProvider(
                    source_defaults=_source(
                        name="Пульс цен (диагностический снимок)",
                        base_url="https://www.pulscen.ru/",
                        source_type=SourceType.DIRECTORY,
                        provider_name=PULSCEN_SNAPSHOT,
                    ),
                    snapshot_path=config.pulscen_snapshot_path,
                )
            )

        return providers

    async def supplier_worker(self) -> SupplierSyncWorker:
        return SupplierSyncWorker(
            providers=self.providers(),
            storage=await self.package_repository(),
            journal=await self.journal(),
            clock=SystemClock(),
            normalizer=await self.normalizer(),
            classifier=await self.classifier(),
            interval_seconds=self._config.sync_interval_seconds,
            max_parallel_sources=self._config.parallel_sources,
        )

    async def aclose(self) -> None:
        pools = [pool for pool in (self._gateway, self._api_gateway) if pool is not None]
        self._gateway = None
        self._api_gateway = None
        for pool in pools:
            await pool.aclose()

    async def __aenter__(self) -> "Container":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()
