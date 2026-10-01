from hypothesis import given
from hypothesis import strategies as st

from src.models.enums import (
    Availability,
    CandidateStatus,
    CheckReason,
    MatchBasis,
    MatchStatus,
    VerificationStatus,
)
from src.models.offer_evidence import OfferEvidence
from src.models.scoring import ChannelRank, Score
from src.service.supplier_search.assembly.assembler import CandidateAssembler
from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.assembly.highlights import HighlightComposer
from src.service.supplier_search.assembly.match import MatchResolver
from src.service.supplier_search.enrichment.bundle import Enrichment
from src.service.supplier_search.fusion.candidate import FusedCandidate, ItemRefs
from src.service.supplier_search.policy.policy import CandidatePolicy
from tests.fakes.domain import make_item, make_offer, make_offer_evidence, make_supplier

ALPHA = make_supplier("alpha")
ITEM = make_item("i1")


def card(
    name: str,
    seller: VerificationStatus,
    match: MatchStatus,
    availability: Availability,
) -> OfferEvidence:
    offer = make_offer(name, supplier=ALPHA, seller_status=seller, availability=availability)
    return make_offer_evidence(offer, match_status=match)


def draft_of(matched: OfferEvidence, unrelated: tuple[OfferEvidence, ...] = ()) -> CandidateDraft:
    fused = FusedCandidate(
        ALPHA.supplier_id,
        Score(1.0),
        (ChannelRank("lexical", 1),),
        {ITEM.item_id: ItemRefs((matched.offer.offer_id,))},
    )
    enrichment = Enrichment(
        suppliers={ALPHA.supplier_id: ALPHA},
        offers={matched.offer.offer_id: matched},
        current={ALPHA.supplier_id: unrelated},
    )
    draft = CandidateAssembler(MatchResolver(), HighlightComposer()).assemble(
        fused, (ITEM,), enrichment
    )
    assert draft is not None
    return draft


def test_unverified_seller_cannot_be_recommended_through_an_unrelated_offer() -> None:
    accepted = card(
        "accepted", VerificationStatus.UNVERIFIED, MatchStatus.ACCEPTED, Availability.UNKNOWN
    )
    unrelated = card(
        "unrelated", VerificationStatus.VERIFIED, MatchStatus.UNMATCHED, Availability.AVAILABLE
    )
    draft = draft_of(accepted, (unrelated,))
    verdict = CandidatePolicy.standard(0.5).evaluate(draft)
    assert [match.basis for match in draft.matches] == [MatchBasis.INFERRED]
    assert verdict.status == CandidateStatus.CHECK
    assert CheckReason.RANGE_UNCONFIRMED in verdict.reasons
    assert CheckReason.NO_CURRENT_OFFER in verdict.reasons


@given(
    seller=st.sampled_from(VerificationStatus),
    match=st.sampled_from(MatchStatus),
    availability=st.sampled_from(Availability),
    unrelated_seller=st.sampled_from(VerificationStatus),
)
def test_recommended_matches_rest_on_offers_of_a_confirmed_seller(
    seller: VerificationStatus,
    match: MatchStatus,
    availability: Availability,
    unrelated_seller: VerificationStatus,
) -> None:
    matched = card("matched", seller, match, availability)
    unrelated = card("other", unrelated_seller, MatchStatus.ACCEPTED, Availability.AVAILABLE)
    draft = draft_of(matched, (unrelated,))
    verdict = CandidatePolicy.standard(0.5).evaluate(draft)
    if verdict.status == CandidateStatus.RECOMMENDED:
        assert draft.role_evidence is not None
        for found in draft.matches:
            assert found.basis in (MatchBasis.STOCK, MatchBasis.CATALOG)
            assert found.offer_id == matched.offer.offer_id
            assert matched.backs_supplier
    evidenced = [found for found in draft.matches if found.basis != MatchBasis.INFERRED]
    assert all(matched.backs_supplier for _ in evidenced)
