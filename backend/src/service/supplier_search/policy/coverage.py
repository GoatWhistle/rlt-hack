from src.models.enums import CheckReason, MatchBasis
from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.policy.outcome import RuleOutcome


class CoverageRule:
    def __init__(self, threshold: float) -> None:
        if not 0 < threshold <= 1:
            raise ValueError("coverage threshold must be within (0, 1]")
        self._threshold = threshold

    def apply(self, draft: CandidateDraft) -> RuleOutcome:
        only_inferred = all(match.basis == MatchBasis.INFERRED for match in draft.matches)
        narrow = draft.coverage < self._threshold
        return RuleOutcome(CheckReason.RANGE_UNCONFIRMED, only_inferred or narrow)
