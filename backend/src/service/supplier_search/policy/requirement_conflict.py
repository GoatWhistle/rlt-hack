from src.models.enums import CheckReason
from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.policy.outcome import RuleOutcome


class RequirementConflictRule:
    def apply(self, draft: CandidateDraft) -> RuleOutcome:
        return RuleOutcome(CheckReason.REQUIREMENT_CONFLICT, draft.conflicting)
