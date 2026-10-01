from collections.abc import Awaitable, Callable

import httpx

from src.adapter.client.ml_service.retriever import MlServiceRetriever
from src.adapter.file.notice_csv.reader import CsvNoticeReader
from src.adapter.repository.clickhouse.history_search.retriever import ClickHouseHistoryRetriever
from src.adapter.repository.clickhouse.offer_read.catalog import ClickHouseOfferCatalog
from src.adapter.repository.clickhouse.offer_search.retriever import ClickHouseLexicalRetriever
from src.adapter.repository.clickhouse.participation.history import ClickHousePurchaseHistory
from src.adapter.repository.clickhouse.probe.probe import ClickHouseProbe
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.search_archive.archive import ClickHouseSearchArchive
from src.adapter.repository.clickhouse.supplier_read.directory import ClickHouseSupplierDirectory
from src.adapter.repository.clickhouse.supplier_read.identity import ClickHouseSupplierIdentity
from src.adapter.repository.clickhouse.upload_store.store import ClickHouseUploadStore
from src.adapter.system.clock import SystemClock
from src.adapter.system.ids import Uuid4Generator
from src.adapter.text.analyzer.analyzer import RussianAnalyzer
from src.adapter.text.rule_interpreter.interpreter import RuleQueryInterpreter
from src.application.config import AppConfig
from src.application.deferred_gateway import Connect, DeferredGateway
from src.service.health.service import HealthService
from src.service.procurement_upload.processor import LotProcessor
from src.service.procurement_upload.runner import LotRunner
from src.service.procurement_upload.service import ProcurementUploadService
from src.service.procurement_upload.settings import UploadSettings
from src.service.supplier_profile.service import SupplierProfileService
from src.service.supplier_search.assembly.assembler import CandidateAssembler
from src.service.supplier_search.assembly.highlights import HighlightComposer
from src.service.supplier_search.assembly.match import MatchResolver
from src.service.supplier_search.assembly.role import RoleResolver
from src.service.supplier_search.fusion.rrf import ReciprocalRankFusion
from src.service.supplier_search.matcher import SupplierMatcher
from src.service.supplier_search.policy.policy import CandidatePolicy
from src.service.supplier_search.protocols import CandidateRetriever
from src.service.supplier_search.ranking.ranker import CandidateRanker
from src.service.supplier_search.service import SupplierSearchService
from src.service.supplier_search.settings import SearchSettings

Release = Callable[[], Awaitable[None]]


class ApiContainer:
    def __init__(self, config: AppConfig, connect: Connect, release: Release | None = None) -> None:
        self._config = config
        self._gateway = DeferredGateway(connect)
        self._release = release
        self._analyzer = RussianAnalyzer()
        self._ml_client: httpx.AsyncClient | None = None
        self._uploads: ProcurementUploadService | None = None
        self._settings = SearchSettings(
            timeout_seconds=config.search.timeout_seconds,
            retrieval_depth_factor=config.search.retrieval_depth_factor,
            coverage_threshold=config.search.coverage_threshold,
        )

    @property
    def gateway(self) -> SqlGateway:
        return self._gateway

    @property
    def database(self) -> str:
        return self._config.clickhouse.database

    def matcher(self) -> SupplierMatcher:
        settings = self._settings
        return SupplierMatcher(
            retrievers=self.retrievers(),
            directory=ClickHouseSupplierDirectory(self._gateway, self.database),
            offers=ClickHouseOfferCatalog(self._gateway, self.database),
            history=ClickHousePurchaseHistory(self._gateway, self._analyzer, self.database),
            fusion=ReciprocalRankFusion(settings.rrf_k),
            assembler=CandidateAssembler(RoleResolver(), MatchResolver(), HighlightComposer()),
            policy=CandidatePolicy.standard(settings.coverage_threshold),
            ranker=CandidateRanker(settings.weights),
            settings=settings,
        )

    async def supplier_search(self) -> SupplierSearchService:
        return SupplierSearchService(
            interpreter=RuleQueryInterpreter(self._analyzer),
            matcher=self.matcher(),
            archive=ClickHouseSearchArchive(self._gateway, self.database),
            clock=SystemClock(),
            ids=Uuid4Generator(),
            settings=self._settings,
        )

    async def procurement_uploads(self) -> ProcurementUploadService:
        if self._uploads is None:
            self._uploads = self._upload_service()
        return self._uploads

    async def supplier_profiles(self) -> SupplierProfileService:
        return SupplierProfileService(
            directory=ClickHouseSupplierDirectory(self._gateway, self.database),
            offers=ClickHouseOfferCatalog(self._gateway, self.database),
            roles=RoleResolver(),
        )

    async def health(self) -> HealthService:
        return HealthService(probes=(ClickHouseProbe(self._gateway),))

    def retrievers(self) -> tuple[CandidateRetriever, ...]:
        search = self._config.search
        channels: list[CandidateRetriever] = [
            ClickHouseLexicalRetriever(
                self._gateway, self._analyzer, self.database, candidate_pool=search.lexical_pool
            )
        ]
        if search.history_enabled:
            channels.append(
                ClickHouseHistoryRetriever(self._gateway, self._analyzer, self.database)
            )
        if self._config.ml_service.enabled:
            channels.append(self._semantic())
        return tuple(channels)

    async def aclose(self) -> None:
        if self._ml_client is not None:
            await self._ml_client.aclose()
            self._ml_client = None
        if self._release is not None:
            await self._release()

    def _upload_service(self) -> ProcurementUploadService:
        upload = self._config.upload
        settings = UploadSettings(
            max_rows=upload.max_rows,
            candidates_per_lot=upload.candidates_per_lot,
            concurrency=upload.concurrency,
            attempts=upload.attempts,
            lot_timeout_seconds=upload.lot_timeout_seconds,
        )
        store = ClickHouseUploadStore(self._gateway, self.database)
        clock = SystemClock()
        processor = LotProcessor(
            RuleQueryInterpreter(self._analyzer), self.matcher(), clock, settings
        )
        return ProcurementUploadService(
            reader=CsvNoticeReader(),
            store=store,
            runner=LotRunner(processor, store, clock, settings),
            clock=clock,
            ids=Uuid4Generator(),
            settings=settings,
        )

    def _semantic(self) -> MlServiceRetriever:
        ml = self._config.ml_service
        if self._ml_client is None:
            self._ml_client = httpx.AsyncClient(base_url=ml.base_url, timeout=ml.timeout_seconds)
        return MlServiceRetriever(
            self._ml_client,
            ClickHouseSupplierIdentity(self._gateway, self.database),
            timeout_seconds=ml.timeout_seconds,
        )
