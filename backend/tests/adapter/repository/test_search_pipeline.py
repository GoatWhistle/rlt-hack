from dataclasses import replace

import pytest

from src.adapter.repository.clickhouse.history_search.retriever import ClickHouseHistoryRetriever
from src.adapter.repository.clickhouse.offer_read.catalog import ClickHouseOfferCatalog
from src.adapter.repository.clickhouse.offer_search.retriever import ClickHouseLexicalRetriever
from src.adapter.repository.clickhouse.participation.history import ClickHousePurchaseHistory
from src.adapter.repository.clickhouse.search_archive.archive import ClickHouseSearchArchive
from src.adapter.repository.clickhouse.supplier_read.directory import ClickHouseSupplierDirectory
from src.adapter.system.clock import SystemClock
from src.adapter.system.ids import Uuid4Generator
from src.adapter.text.analyzer.analyzer import RussianAnalyzer
from src.adapter.text.rule_interpreter.interpreter import RuleQueryInterpreter
from src.models.enums import CandidateStatus, CheckReason, MatchBasis
from src.models.search import SearchQuery, SearchText
from src.service.supplier_search.assembly.assembler import CandidateAssembler
from src.service.supplier_search.assembly.highlights import HighlightComposer
from src.service.supplier_search.assembly.match import MatchResolver
from src.service.supplier_search.fusion.rrf import ReciprocalRankFusion
from src.service.supplier_search.matcher import SupplierMatcher
from src.service.supplier_search.pipeline import SearchPipeline
from src.service.supplier_search.policy.policy import CandidatePolicy
from src.service.supplier_search.ranking.ranker import CandidateRanker
from src.service.supplier_search.service import SupplierSearchService
from src.service.supplier_search.settings import SearchSettings
from tests.adapter.repository.seed import Seeder
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.fakes.domain import make_offer, make_source, make_supplier

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb

ALPHA = make_supplier("alpha", inn="7801234564")
GAMMA = make_supplier("gamma", inn=None)


def build_service(gateway: ChdbGateway) -> SupplierSearchService:
    analyzer = RussianAnalyzer()
    settings = SearchSettings()
    matcher = SupplierMatcher(
        retrievers=(
            ClickHouseLexicalRetriever(gateway, analyzer),
            ClickHouseHistoryRetriever(gateway, analyzer),
        ),
        directory=ClickHouseSupplierDirectory(gateway),
        offers=ClickHouseOfferCatalog(gateway),
        history=ClickHousePurchaseHistory(gateway, analyzer),
        fusion=ReciprocalRankFusion(settings.rrf_k),
        assembler=CandidateAssembler(MatchResolver(), HighlightComposer()),
        policy=CandidatePolicy.standard(settings.coverage_threshold),
        ranker=CandidateRanker(settings.weights),
        settings=settings,
    )
    return SupplierSearchService(
        pipeline=SearchPipeline(RuleQueryInterpreter(analyzer), matcher, SystemClock(), settings),
        archive=ClickHouseSearchArchive(gateway),
        ids=Uuid4Generator(),
        settings=settings,
    )


async def seed(gateway: ChdbGateway) -> None:
    seeder = Seeder(gateway)
    await seeder.suppliers(ALPHA, GAMMA)
    await seeder.sources(make_source())
    buckwheat = replace(make_offer("buckwheat", supplier=ALPHA), name="Крупа гречневая ядрица")
    rice = replace(make_offer("rice", supplier=ALPHA), name="Рис шлифованный")
    await seeder.offers(buckwheat, rice)
    await seeder.match(rice.offer_id, "accepted")
    await seeder.lot("L1", "Поставка крупы гречневой для школ")
    await seeder.participation("L1", GAMMA, won=True)
    await seeder.refresh_history()


async def test_text_query_finds_explains_and_archives_suppliers(gateway: ChdbGateway) -> None:
    await seed(gateway)
    service = build_service(gateway)
    text = "Крупа гречневая ядрица 500 кг, рис шлифованный 200 кг, доставка в Санкт-Петербург"
    result = await service.search(SearchQuery(SearchText(text)))
    assert [item.name for item in result.items] == ["Крупа гречневая ядрица", "Рис шлифованный"]
    assert [candidate.supplier for candidate in result.candidates] == [ALPHA, GAMMA]
    alpha, gamma = result.candidates
    assert alpha.status == CandidateStatus.RECOMMENDED
    assert {match.basis for match in alpha.matches} == {MatchBasis.STOCK}
    assert gamma.status == CandidateStatus.CHECK
    assert CheckReason.INN_MISSING in gamma.check_reasons
    assert gamma.history.wins == 1
    assert [match.basis for match in gamma.matches] == [MatchBasis.INFERRED]
    assert result.warnings == ()
    assert await service.get(result.search_id) == result
    assert (await service.recent(5))[0].search_id == result.search_id
