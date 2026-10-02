from dataclasses import replace

from src.models.enums import MatchBasis
from src.models.search.offer_summary import OfferSummary
from src.service.supplier_search.assembly.offers import matched_offers
from tests.fakes.domain import make_candidate, make_offer, make_offer_evidence, make_supplier, uid


def test_matched_offers_follow_candidates_once_each() -> None:
    alpha = make_supplier("alpha")
    beta = make_supplier("beta")
    first = make_candidate(alpha)
    second = replace(
        make_candidate(beta, rank=2),
        matches=(
            *first.matches,
            replace(first.matches[0], item_id="i2", offer_id=uid("offer:missing")),
            replace(first.matches[0], item_id="i3", basis=MatchBasis.INFERRED, offer_id=None),
        ),
    )
    card = make_offer_evidence(make_offer(supplier=alpha))
    offers = matched_offers((first, second), {card.offer.offer_id: card})
    assert offers == (OfferSummary.of(card),)
    assert matched_offers((), {card.offer.offer_id: card}) == ()
