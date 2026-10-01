from src.models.enums import CheckReason, CompanyRole
from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.policy.outcome import RuleOutcome


class RoleConfirmedRule:
    def apply(self, draft: CandidateDraft) -> RuleOutcome:
        unconfirmed = draft.role == CompanyRole.UNKNOWN or draft.role_evidence is None
        return RuleOutcome(CheckReason.ROLE_UNCONFIRMED, unconfirmed)
