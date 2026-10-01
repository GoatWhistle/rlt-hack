import math
from dataclasses import replace
from typing import cast

import pytest

from src.models.candidate import Highlight, ProductMatch
from src.models.enums import (
    Availability,
    CandidateStatus,
    CheckReason,
    EvidenceKind,
    HighlightCode,
    MatchBasis,
    MatchStatus,
    PurchaseOutcome,
    SourceType,
    VerificationStatus,
)
from src.models.errors import (
    InvalidCandidateError,
    InvalidMatchError,
    InvalidPurchaseSummaryError,
    InvalidRankError,
    InvalidScoreError,
)
from src.models.purchase import PurchaseRecord, PurchaseSummary
from src.models.retrieval import ChannelHit, ItemHit, RetrievalHits
from src.models.scoring import ChannelRank, Score
from tests.fakes.domain import (
    make_candidate,
    make_evidence,
    make_offer,
    make_offer_evidence,
    make_source,
    make_supplier,
    uid,
)


def test_score_stays_within_unit_interval() -> None:
    assert Score.clamp(1.7) == Score(1.0)
    assert Score.clamp(-2) == Score.zero()
    assert Score.clamp(math.nan) == Score.zero()
    assert Score.ratio(1, 4) == Score(0.25)
    assert Score.ratio(1, 0) == Score.zero()
    assert Score(0.2) < Score(0.3)
    for value in (-0.1, 1.1, math.inf):
        with pytest.raises(InvalidScoreError):
            Score(value)


def test_channel_rank_and_hits_start_at_one() -> None:
    with pytest.raises(InvalidRankError):
        ChannelRank("lexical", 0)
    with pytest.raises(InvalidRankError):
        ChannelRank("", 1)
    with pytest.raises(InvalidRankError):
        ItemHit("i1", -1.0)
    with pytest.raises(InvalidRankError):
        ItemHit("", 1.0)
    with pytest.raises(InvalidRankError):
        ChannelHit(uid("a"), 0)


def test_retrieval_hits_are_ranked_once_per_supplier() -> None:
    first = ChannelHit(uid("a"), 1, (ItemHit("i1", 2.0), ItemHit("i2", 1.0)))
    hits = RetrievalHits("lexical", (first, ChannelHit(uid("b"), 2)))
    assert hits.hits[0].item_ids == frozenset({"i1", "i2"})
    with pytest.raises(InvalidRankError):
        RetrievalHits("lexical", (ChannelHit(uid("a"), 2),))
    with pytest.raises(InvalidRankError):
        RetrievalHits("lexical", (first, ChannelHit(uid("a"), 2)))
    with pytest.raises(InvalidRankError):
        RetrievalHits("")


def test_evidenced_match_needs_offer_and_source() -> None:
    assert ProductMatch("i1", MatchBasis.INFERRED).evidence is None
    with pytest.raises(InvalidMatchError):
        ProductMatch("i1", MatchBasis.STOCK)
    with pytest.raises(InvalidMatchError):
        ProductMatch("i1", MatchBasis.CATALOG, offer_id=uid("o"))
    with pytest.raises(InvalidMatchError):
        ProductMatch("", MatchBasis.INFERRED)


def test_highlight_params_are_read_only() -> None:
    highlight = Highlight(HighlightCode.COVERS_ITEMS, {"matched": 1})
    with pytest.raises(TypeError):
        cast("dict[str, int]", highlight.params)["matched"] = 2


def test_purchase_summary_counts_are_consistent() -> None:
    record = PurchaseRecord("lot-1", "Поставка", PurchaseOutcome.WINNER, ("i1",))
    summary = PurchaseSummary(similar=2, wins=1, records=(record,))
    assert summary.item_ids == frozenset({"i1"})
    assert PurchaseSummary.empty().similar == 0
    for similar, wins, records in ((-1, 0, ()), (1, 2, ()), (0, 0, (record,))):
        with pytest.raises(InvalidPurchaseSummaryError):
            PurchaseSummary(similar=similar, wins=wins, records=records)


def test_candidate_is_recommended_exactly_without_reasons() -> None:
    candidate = make_candidate()
    assert candidate.status == CandidateStatus.RECOMMENDED
    assert candidate.matched_item_ids == frozenset({"i1"})
    assert candidate.supplier_id == candidate.supplier.supplier_id
    flagged = make_candidate(reasons=(CheckReason.INN_MISSING,))
    assert flagged.status == CandidateStatus.CHECK
    with pytest.raises(InvalidCandidateError):
        replace(candidate, status=CandidateStatus.CHECK)
    with pytest.raises(InvalidCandidateError):
        replace(flagged, status=CandidateStatus.RECOMMENDED)
    with pytest.raises(InvalidCandidateError):
        replace(flagged, check_reasons=(CheckReason.INN_MISSING, CheckReason.INN_MISSING))
    with pytest.raises(InvalidCandidateError):
        replace(candidate, rank=0)
    with pytest.raises(InvalidCandidateError):
        replace(candidate, matches=candidate.matches * 2)


def test_offer_evidence_reads_seller_stock_and_conflicts() -> None:
    supplier = make_supplier()
    evidence = make_offer_evidence(make_offer(supplier=supplier))
    assert evidence.is_current
    assert evidence.in_stock
    assert evidence.seller_confirmed
    assert evidence.catalog_confirmed
    assert not evidence.has_conflict
    withdrawn = make_offer_evidence(
        make_offer(
            availability=Availability.UNAVAILABLE, seller_status=VerificationStatus.CONFLICT
        ),
        match_status=MatchStatus.REVIEW,
    )
    assert not withdrawn.is_current
    assert not withdrawn.in_stock
    assert withdrawn.has_conflict
    assert not withdrawn.catalog_confirmed


def test_offer_evidence_points_to_the_offer_and_its_role_source() -> None:
    priced = make_offer_evidence()
    assert priced.evidence is not None
    assert priced.evidence.kind == EvidenceKind.PRICE
    assert priced.evidence.checked_at == priced.offer.last_seen_at
    unpriced = make_offer_evidence(
        replace(make_offer(), price=None), source=make_source("feed", SourceType.REGISTRY)
    )
    assert unpriced.evidence is not None
    assert unpriced.evidence.kind == EvidenceKind.REGISTRY
    role = priced.role_evidence
    assert role is not None
    assert role.title == "Дистрибьютор"
    hidden = make_offer_evidence(replace(make_offer(), url="/local"))
    assert hidden.evidence is None
    assert hidden.role_evidence is None
    assert make_evidence().url.startswith("https://")
