from typing import cast

import pytest

from src.models.ranking.retrieval import ChannelHit, ItemHit, RetrievalHits
from src.models.ranking.scoring import ChannelRank, Score
from src.service.supplier_search.fusion.candidate import FusedCandidate, ItemRefs
from src.service.supplier_search.fusion.rrf import ReciprocalRankFusion
from tests.fakes.domain import uid

ALPHA = uid("alpha")
BETA = uid("beta")
GAMMA = uid("gamma")
OFFER_A = uid("offer:a")
OFFER_B = uid("offer:b")


def test_supplier_found_by_both_channels_wins() -> None:
    lexical = RetrievalHits(
        "lexical",
        (
            ChannelHit(BETA, 1, (ItemHit("i1", 2.0, offer_ids=(OFFER_A,)),)),
            ChannelHit(ALPHA, 2, (ItemHit("i1", 1.0, offer_ids=(OFFER_B,)),)),
        ),
    )
    history = RetrievalHits(
        "history",
        (
            ChannelHit(ALPHA, 1, (ItemHit("i2", 3.0, lot_ids=("lot-1",)),)),
            ChannelHit(GAMMA, 2),
        ),
    )
    fused = ReciprocalRankFusion(k=60).fuse((lexical, history))
    assert [candidate.supplier_id for candidate in fused] == [ALPHA, BETA, GAMMA]
    top = fused[0]
    assert top.channels == (ChannelRank("lexical", 2), ChannelRank("history", 1))
    assert top.items["i1"] == ItemRefs(offer_ids=(OFFER_B,))
    assert top.items["i2"] == ItemRefs(lot_ids=("lot-1",))
    assert top.fusion.value == pytest.approx((1 / 62 + 1 / 61) / (2 / 61))


def test_fusion_is_normalised_to_the_best_possible_rank() -> None:
    hits = RetrievalHits("lexical", (ChannelHit(ALPHA, 1), ChannelHit(BETA, 2)))
    fused = ReciprocalRankFusion(k=1).fuse((hits,))
    assert fused[0].fusion == Score(1.0)
    assert fused[1].fusion.value == pytest.approx(2 / 3)


def test_refs_of_one_item_merge_across_channels_without_duplicates() -> None:
    first = RetrievalHits("a", (ChannelHit(ALPHA, 1, (ItemHit("i1", 1.0, (OFFER_A,)),)),))
    second = RetrievalHits(
        "b", (ChannelHit(ALPHA, 1, (ItemHit("i1", 1.0, (OFFER_A, OFFER_B), ("lot",)),)),)
    )
    fused = ReciprocalRankFusion().fuse((first, second))
    assert fused[0].items["i1"] == ItemRefs((OFFER_A, OFFER_B), ("lot",))
    assert fused[0].offer_ids == (OFFER_A, OFFER_B)


def test_ties_are_broken_by_supplier_id_and_empty_input_gives_nothing() -> None:
    first = RetrievalHits("a", (ChannelHit(BETA, 1),))
    second = RetrievalHits("b", (ChannelHit(ALPHA, 1),))
    fused = ReciprocalRankFusion().fuse((first, second))
    assert [item.supplier_id for item in fused] == sorted((ALPHA, BETA), key=str)
    assert ReciprocalRankFusion().fuse(()) == ()


def test_fusion_rejects_non_positive_k_and_freezes_items() -> None:
    with pytest.raises(ValueError, match="positive"):
        ReciprocalRankFusion(k=0)
    candidate = FusedCandidate(ALPHA, Score(0.5), items={"i1": ItemRefs()})
    with pytest.raises(TypeError):
        cast(dict[str, ItemRefs], candidate.items)["i2"] = ItemRefs()
