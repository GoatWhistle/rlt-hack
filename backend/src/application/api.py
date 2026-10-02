from collections.abc import Awaitable, Callable

import httpx

from src.adapter.client.catalog_vectors.retriever import CatalogVectorRetriever
from src.adapter.client.ml_service.retriever import MlServiceRetriever, no_correlation
from src.adapter.repository.clickhouse.history_search.retriever import ClickHouseHistoryRetriever
from src.adapter.repository.clickhouse.offer_read.catalog import ClickHouseOfferCatalog
from src.adapter.repository.clickhouse.offer_search.retriever import ClickHouseLexicalRetriever
from src.adapter.repository.clickhouse.participation.history import ClickHousePurchaseHistory
from src.adapter.repository.clickhouse.probe.probe import ClickHouseProbe
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.search_archive.archive import ClickHouseSearchArchive
from src.adapter.repository.clickhouse.supplier_read.directory import ClickHouseSupplierDirectory
from src.adapter.repository.clickhouse.supplier_read.identity import ClickHouseSupplierIdentity
from src.adapter.system.clock import SystemClock
from src.adapter.system.ids import Uuid4Generator
from src.adapter.text.analyzer.analyzer import RussianAnalyzer
from src.adapter.text.rule_interpreter.interpreter import RuleQueryInterpreter
from src.application.config import AppConfig
from src.application.deferred_gateway import Connect, DeferredGateway
from src.service.health.service import HealthService
from src.service.supplier_profile.service import SupplierProfileService
from src.service.supplier_search.assembly.assembler import CandidateAssembler
from src.service.supplier_search.assembly.highlights import HighlightComposer
from src.service.supplier_search.assembly.match import MatchResolver
from src.service.supplier_search.fusion.rrf import ReciprocalRankFusion
from src.service.supplier_search.matcher import SupplierMatcher
from src.service.supplier_search.pipeline import SearchPipeline
from src.service.supplier_search.policy.policy import CandidatePolicy
from src.service.supplier_search.protocols import CandidateRetriever
from src.service.supplier_search.ranking.ranker import CandidateRanker
from src.service.supplier_search.service import SupplierSearchService
from src.service.supplier_search.settings import SearchSettings

Release = Callable[[], Awaitable[None]]


class ApiContainer:
    def __init__(
        self,
        config: AppConfig,
        connect: Connect,
        release: Release | None = None,
        *,
        background: Connect | None = None,
        control: Connect | None = None,
        correlation: Callable[[], str | None] | None = None,
    ) -> None:
        self._config = config
        self._gateway = DeferredGateway(connect)
        self._background = self._gateway if background is None else DeferredGateway(background)
        self._control = self._gateway if control is None else DeferredGateway(control)
        self._release = release
        self._correlation = correlation
        self._analyzer = RussianAnalyzer()
        self._ml_client: httpx.AsyncClient | None = None
        self._vector_client: httpx.AsyncClient | None = None
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

    def matcher(self, gateway: SqlGateway | None = None) -> SupplierMatcher:
        settings = self._settings
        sql = gateway or self._gateway
        return SupplierMatcher(
            retrievers=self.retrievers(sql),
            directory=ClickHouseSupplierDirectory(sql, self.database),
            offers=ClickHouseOfferCatalog(sql, self.database),
            history=ClickHousePurchaseHistory(sql, self._analyzer, self.database),
            fusion=ReciprocalRankFusion(settings.rrf_k),
            assembler=CandidateAssembler(MatchResolver(), HighlightComposer()),
            policy=CandidatePolicy.standard(settings.coverage_threshold),
            ranker=CandidateRanker(settings.weights),
            settings=settings,
        )

    def pipeline(self, gateway: SqlGateway | None = None) -> SearchPipeline:
        return SearchPipeline(
            interpreter=RuleQueryInterpreter(self._analyzer),
            matcher=self.matcher(gateway),
            clock=SystemClock(),
            settings=self._settings,
        )

    async def supplier_search(self) -> SupplierSearchService:
        return SupplierSearchService(
            pipeline=self.pipeline(),
            archive=ClickHouseSearchArchive(self._gateway, self.database),
            ids=Uuid4Generator(),
            settings=self._settings,
        )

    async def supplier_profiles(self) -> SupplierProfileService:
        return SupplierProfileService(
            directory=ClickHouseSupplierDirectory(self._gateway, self.database),
            offers=ClickHouseOfferCatalog(self._gateway, self.database),
        )

    async def background(self) -> tuple[()]:
        return ()

    async def health(self) -> HealthService:
        return HealthService(probes=(ClickHouseProbe(self._control),))

    def retrievers(self, gateway: SqlGateway | None = None) -> tuple[CandidateRetriever, ...]:
        search = self._config.search
        sql = gateway or self._gateway
        channels: list[CandidateRetriever] = [
            ClickHouseLexicalRetriever(
                sql, self._analyzer, self.database, candidate_pool=search.lexical_pool
            )
        ]
        if search.history_enabled:
            channels.append(ClickHouseHistoryRetriever(sql, self._analyzer, self.database))
        if self._config.ml_service.enabled:
            channels.append(self._semantic(sql))
        if search.vector_url:
            if self._vector_client is None:
                self._vector_client = httpx.AsyncClient(
                    base_url=search.vector_url, timeout=httpx.Timeout(5, connect=2), trust_env=False
                )
            channels.append(CatalogVectorRetriever(self._vector_client))
        return tuple(channels)

    async def aclose(self) -> None:
        if self._vector_client is not None:
            await self._vector_client.aclose()
            self._vector_client = None
        if self._ml_client is not None:
            await self._ml_client.aclose()
            self._ml_client = None
        if self._release is not None:
            await self._release()

    def _semantic(self, gateway: SqlGateway) -> MlServiceRetriever:
        ml = self._config.ml_service
        if self._ml_client is None:
            self._ml_client = httpx.AsyncClient(
                base_url=ml.base_url, timeout=ml.timeout_seconds, trust_env=False
            )
        return MlServiceRetriever(
            self._ml_client,
            ClickHouseSupplierIdentity(gateway, self.database),
            timeout_seconds=ml.timeout_seconds,
            correlation=self._correlation or no_correlation,
        )
