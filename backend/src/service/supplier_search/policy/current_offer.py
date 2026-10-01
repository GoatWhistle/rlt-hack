from src.models.enums import CheckReason
from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.policy.outcome import RuleOutcome


class CurrentOfferRule:
    def apply(self, draft: CandidateDraft) -> RuleOutcome:
        cards = (*draft.current_offers, *draft.used_offers)
        present = any(card.is_current and card.seller_confirmed for card in cards)
        return RuleOutcome(CheckReason.NO_CURRENT_OFFER, not present)
