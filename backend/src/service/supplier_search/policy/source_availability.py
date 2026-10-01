from src.models.enums import CheckReason
from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.policy.outcome import RuleOutcome


class SourceAvailabilityRule:
    def apply(self, draft: CandidateDraft) -> RuleOutcome:
        return RuleOutcome(CheckReason.SOURCE_UNAVAILABLE, draft.enrichment_failed)
