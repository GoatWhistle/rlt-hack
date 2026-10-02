from collections.abc import Mapping, Sequence
from uuid import UUID

from src.models.company.offer_evidence import OfferEvidence
from src.models.search.candidate import SupplierCandidate
from src.models.search.offer_summary import OfferSummary


def matched_offers(
    candidates: Sequence[SupplierCandidate], cards: Mapping[UUID, OfferEvidence]
) -> tuple[OfferSummary, ...]:
    ids = dict.fromkeys(
        match.offer_id
        for candidate in candidates
        for match in candidate.matches
        if match.offer_id is not None
    )
    return tuple(OfferSummary.of(cards[offer_id]) for offer_id in ids if offer_id in cards)
