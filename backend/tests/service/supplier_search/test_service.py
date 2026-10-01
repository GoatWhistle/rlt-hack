from dataclasses import dataclass, field, replace

import pytest

from src.models.enums import (
    CandidateStatus,
    CheckReason,
    ItemOrigin,
    MatchBasis,
    WarningCode,
)
from src.models.offer_evidence import OfferEvidence
from src.models.purchase import PurchaseSummary
from src.models.retrieval import ChannelHit, ItemHit, RetrievalHits
from src.models.search_result import SearchWarning
from src.service.errors import (
    SearchNotFoundError,
    SearchTimeoutError,
    SearchUnavailableError,
    UninterpretableQueryError,
)
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
from tests.fakes.domain import (
    MOMENT,
    make_item,
    make_offer,
    make_offer_evidence,
    make_query,
    make_supplier,
    uid,
)
from tests.fakes.ports import (
    FakeArchive,
    FakeDirectory,
    FakeHistory,
    FakeInterpreter,
    FakeOfferCatalog,
    FakeRetriever,
    FixedClock,
    SequentialIds,
)

ALPHA = make_supplier("alpha")
BETA = make_supplier("beta", inn=None)
GHOST = uid("ghost")
ITEMS = (make_item("i1", "Крупа гречневая"), make_item("i2", "Рис"))


def alpha_card() -> OfferEvidence:
    return make_offer_evidence(make_offer("grechka", supplier=ALPHA))


def lexical_hits() -> RetrievalHits:
    return RetrievalHits(
        "lexical",
        (
            ChannelHit(ALPHA.supplier_id, 1, (ItemHit("i1", 3.0, (alpha_card().offer.offer_id,)),)),
            ChannelHit(BETA.supplier_id, 2, (ItemHit("i1", 1.0),)),
            ChannelHit(GHOST, 3, (ItemHit("i2", 1.0),)),
        ),
    )


def history_hits() -> RetrievalHits:
    return RetrievalHits(
        "history", (ChannelHit(BETA.supplier_id, 1, (ItemHit("i2", 2.0, lot_ids=("lot-1",)),)),)
    )


@dataclass(slots=True)
class Harness:
    interpreter: FakeInterpreter = field(default_factory=lambda: FakeInterpreter(ITEMS))
    lexical: FakeRetriever = field(default_factory=lambda: FakeRetriever("lexical", lexical_hits()))
    history_channel: FakeRetriever = field(
        default_factory=lambda: FakeRetriever("history", history_hits())
    )
    directory: FakeDirectory = field(default_factory=lambda: FakeDirectory((ALPHA, BETA)))
    offers: FakeOfferCatalog = field(default_factory=lambda: FakeOfferCatalog((alpha_card(),)))
    history: FakeHistory = field(
        default_factory=lambda: FakeHistory({BETA.supplier_id: PurchaseSummary(similar=3)})
    )
    archive: FakeArchive = field(default_factory=FakeArchive)
    settings: SearchSettings = field(default_factory=SearchSettings)

    def pipeline(self) -> SearchPipeline:
        matcher = SupplierMatcher(
            retrievers=(self.lexical, self.history_channel),
            directory=self.directory,
            offers=self.offers,
            history=self.history,
            fusion=ReciprocalRankFusion(self.settings.rrf_k),
            assembler=CandidateAssembler(MatchResolver(), HighlightComposer()),
            policy=CandidatePolicy.standard(self.settings.coverage_threshold),
            ranker=CandidateRanker(self.settings.weights),
            settings=self.settings,
        )
        return SearchPipeline(self.interpreter, matcher, FixedClock(), self.settings)

    def service(self) -> SupplierSearchService:
        return SupplierSearchService(
            pipeline=self.pipeline(),
            archive=self.archive,
            ids=SequentialIds(),
            settings=self.settings,
        )


async def test_search_ranks_explains_and_archives_candidates() -> None:
    harness = Harness()
    result = await harness.service().search(make_query(limit=5))
    assert [candidate.supplier for candidate in result.candidates] == [ALPHA, BETA]
    alpha, beta = result.candidates
    assert alpha.status == CandidateStatus.RECOMMENDED
    assert [(match.item_id, match.basis) for match in alpha.matches] == [("i1", MatchBasis.STOCK)]
    assert beta.status == CandidateStatus.CHECK
    assert CheckReason.INN_MISSING in beta.check_reasons
    assert {match.basis for match in beta.matches} == {MatchBasis.INFERRED}
    assert result.pipeline.channels == ("lexical", "history")
    assert (result.created_at, result.pipeline.as_of, result.warnings) == (MOMENT, MOMENT, ())
    assert harness.archive.stored == {result.search_id: result}
    assert harness.lexical.calls[0][1] == 15
    assert harness.lexical.calls[0][0].items == ITEMS


async def test_failed_channel_becomes_a_warning() -> None:
    harness = Harness(history_channel=FakeRetriever("history", fails=True))
    result = await harness.service().search(make_query())
    assert result.warnings == (SearchWarning(WarningCode.CHANNEL_FAILED, "history"),)
    assert result.pipeline.channels == ("lexical",)
    assert [candidate.supplier for candidate in result.candidates] == [ALPHA, BETA]


async def test_every_channel_failing_makes_search_unavailable() -> None:
    harness = Harness(
        lexical=FakeRetriever("lexical", fails=True),
        history_channel=FakeRetriever("history", fails=True),
    )
    with pytest.raises(SearchUnavailableError) as raised:
        await harness.service().search(make_query())
    assert raised.value.channels == ("lexical", "history")
    assert harness.archive.stored == {}


async def test_failed_enrichment_marks_candidates_for_checking() -> None:
    harness = Harness(
        offers=FakeOfferCatalog((alpha_card(),), fails_lookup=True),
        history=FakeHistory(fails=True),
    )
    result = await harness.service().search(make_query())
    assert result.warnings == (
        SearchWarning(WarningCode.ENRICHMENT_FAILED, "offers"),
        SearchWarning(WarningCode.ENRICHMENT_FAILED, "history"),
    )
    for candidate in result.candidates:
        assert CheckReason.SOURCE_UNAVAILABLE in candidate.check_reasons


async def test_without_directory_nobody_can_be_shown() -> None:
    harness = Harness(directory=FakeDirectory(fails=True))
    result = await harness.service().search(make_query())
    assert result.candidates == ()
    assert result.warnings == (SearchWarning(WarningCode.ENRICHMENT_FAILED, "directory"),)


async def test_archive_failure_still_returns_the_result() -> None:
    harness = Harness(archive=FakeArchive(fails=True))
    result = await harness.service().search(make_query())
    assert result.warnings == (SearchWarning(WarningCode.ARCHIVE_FAILED),)
    assert len(result.candidates) == 2


async def test_slow_archive_returns_result_with_warning() -> None:
    harness = Harness(
        archive=FakeArchive(delay=1.0),
        settings=SearchSettings(timeout_seconds=0.5, archive_timeout_seconds=0.05),
    )
    result = await harness.service().search(make_query())
    assert result.warnings == (SearchWarning(WarningCode.ARCHIVE_FAILED),)
    assert harness.archive.stored == {}


async def test_slow_search_times_out() -> None:
    harness = Harness(
        lexical=FakeRetriever("lexical", lexical_hits(), delay=1.0),
        settings=SearchSettings(timeout_seconds=0.05),
    )
    with pytest.raises(SearchTimeoutError) as raised:
        await harness.service().search(make_query())
    assert raised.value.seconds == 0.05


async def test_text_without_items_cannot_be_searched() -> None:
    harness = Harness(interpreter=FakeInterpreter(()))
    with pytest.raises(UninterpretableQueryError):
        await harness.service().search(make_query())
    assert harness.lexical.calls == []


async def test_no_hits_skip_enrichment() -> None:
    harness = Harness(
        lexical=FakeRetriever("lexical"),
        history_channel=FakeRetriever("history"),
    )
    result = await harness.service().search(make_query())
    assert result.candidates == ()
    assert harness.offers.lookups == []


async def test_inferred_items_are_reported() -> None:
    inferred = replace(make_item(), origin=ItemOrigin.INFERRED)
    harness = Harness(interpreter=FakeInterpreter((inferred,)))
    result = await harness.service().search(make_query())
    assert result.warnings == (SearchWarning(WarningCode.ITEMS_INFERRED),)


async def test_limit_cuts_candidates() -> None:
    result = await Harness().service().search(make_query(limit=1))
    assert [candidate.supplier for candidate in result.candidates] == [ALPHA]


async def test_saved_searches_can_be_read_back() -> None:
    harness = Harness()
    service = harness.service()
    result = await service.search(make_query())
    assert await service.get(result.search_id) == result
    assert await service.recent(10) == (result.summary(),)
    with pytest.raises(SearchNotFoundError):
        await service.get(uid("missing"))
