from src.models.enums import CheckReason, VerificationStatus
from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.policy.outcome import RuleOutcome


class IdentityConflictRule:
    def apply(self, draft: CandidateDraft) -> RuleOutcome:
        conflicted = draft.supplier.identity_status == VerificationStatus.CONFLICT or any(
            card.has_conflict for card in draft.used_offers
        )
        return RuleOutcome(CheckReason.IDENTITY_CONFLICT, conflicted)
