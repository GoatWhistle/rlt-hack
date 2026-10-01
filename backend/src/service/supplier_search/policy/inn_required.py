from src.models.enums import CheckReason
from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.policy.outcome import RuleOutcome


class InnRequiredRule:
    def apply(self, draft: CandidateDraft) -> RuleOutcome:
        return RuleOutcome(CheckReason.INN_MISSING, not draft.supplier.has_valid_inn)
