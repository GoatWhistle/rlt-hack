import pytest

from src.models.candidate import ProductMatch
from src.models.enums import CandidateStatus, CheckReason, MatchBasis
from src.models.purchase import PurchaseSummary
from src.models.scoring import Score
from src.service.supplier_search.policy.outcome import PolicyVerdict
from src.service.supplier_search.ranking.components import (
    coverage_score,
    evidence_score,
    history_score,
)
from src.service.supplier_search.ranking.ranker import CandidateRanker
from src.service.supplier_search.settings import ScoreWeights
from tests.fakes.domain import make_supplier
from tests.fakes.drafts import make_draft, stock_match

CLEAR = PolicyVerdict()
CHECK = PolicyVerdict((CheckReason.INN_MISSING,))


def test_evidence_averages_basis_weights_over_matched_items() -> None:
    matches = (
        stock_match("i1"),
        ProductMatch("i2", MatchBasis.INFERRED),
    )
    assert evidence_score(matches).value == pytest.approx(0.6)
    assert evidence_score(()) == Score.zero()


def test_coverage_counts_distinct_items() -> None:
    assert coverage_score((stock_match("i1"),), 4) == Score(0.25)
    assert coverage_score((), 0) == Score.zero()


def test_history_saturates_with_similar_purchases_and_wins() -> None:
    assert history_score(PurchaseSummary()) == Score.zero()
    modest = history_score(PurchaseSummary(similar=5, wins=2))
    assert modest.value == pytest.approx(0.5)
    heavy = history_score(PurchaseSummary(similar=500, wins=200))
    assert modest < heavy < Score(1.0)


def test_total_is_the_weighted_mean_of_components() -> None:
    ranker = CandidateRanker(ScoreWeights(fusion=1, coverage=1, evidence=0, history=0))
    score = ranker.score(make_draft(fusion=0.5, total_items=2))
    assert score.coverage == Score(0.5)
    assert score.evidence == Score(1.0)
    assert score.total.value == pytest.approx(0.5)
    assert [channel.channel for channel in score.channels] == ["lexical"]


def test_recommended_candidates_come_first_then_by_total_then_by_inn() -> None:
    ranker = CandidateRanker(ScoreWeights())
    strong_check = make_draft(make_supplier("strong", inn="7800000001"), fusion=1.0)
    weak_clear = make_draft(make_supplier("weak", inn="7800000003"), fusion=0.1)
    twin_b = make_draft(make_supplier("twin-b", inn="7800000005"), fusion=0.5)
    twin_a = make_draft(make_supplier("twin-a", inn="7800000004"), fusion=0.5)
    ranked = ranker.rank(
        [(strong_check, CHECK), (weak_clear, CLEAR), (twin_b, CLEAR), (twin_a, CLEAR)], 10
    )
    assert [candidate.supplier.inn for candidate in ranked] == [
        "7800000004",
        "7800000005",
        "7800000003",
        "7800000001",
    ]
    assert [candidate.rank for candidate in ranked] == [1, 2, 3, 4]
    assert ranked[-1].status == CandidateStatus.CHECK
    assert ranked[-1].check_reasons == (CheckReason.INN_MISSING,)


def test_ranking_cuts_to_the_limit() -> None:
    ranker = CandidateRanker(ScoreWeights())
    drafts = [(make_draft(make_supplier(f"s{index}")), CLEAR) for index in range(5)]
    assert len(ranker.rank(drafts, 2)) == 2
    assert ranker.rank(drafts, 0) == ()
