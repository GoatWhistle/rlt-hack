from src.models.enums import CheckReason
from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.policy.outcome import RuleOutcome


class CurrentOfferRule:
    def apply(self, draft: CandidateDraft) -> RuleOutcome:
        matched = {match.offer_id for match in draft.matches if match.offer_id is not None}
        cards = (*draft.used_offers, *draft.current_offers)
        present = any(
            card.is_current and card.backs_supplier
            for card in cards
            if card.offer.offer_id in matched
        )
        return RuleOutcome(CheckReason.NO_CURRENT_OFFER, not present)
