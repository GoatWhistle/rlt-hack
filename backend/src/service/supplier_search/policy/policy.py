from collections.abc import Sequence
from typing import Self

from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.policy.coverage import CoverageRule
from src.service.supplier_search.policy.current_offer import CurrentOfferRule
from src.service.supplier_search.policy.identity_conflict import IdentityConflictRule
from src.service.supplier_search.policy.inn_required import InnRequiredRule
from src.service.supplier_search.policy.outcome import PolicyVerdict
from src.service.supplier_search.policy.protocols import PolicyRule
from src.service.supplier_search.policy.role_confirmed import RoleConfirmedRule
from src.service.supplier_search.policy.source_availability import SourceAvailabilityRule


class CandidatePolicy:
    def __init__(self, rules: Sequence[PolicyRule]) -> None:
        self._rules = tuple(rules)

    @classmethod
    def standard(cls, coverage_threshold: float) -> Self:
        return cls(
            (
                InnRequiredRule(),
                IdentityConflictRule(),
                RoleConfirmedRule(),
                CurrentOfferRule(),
                CoverageRule(coverage_threshold),
                SourceAvailabilityRule(),
            )
        )

    def evaluate(self, draft: CandidateDraft) -> PolicyVerdict:
        outcomes = (rule.apply(draft) for rule in self._rules)
        reasons = tuple(dict.fromkeys(outcome.reason for outcome in outcomes if outcome.triggered))
        return PolicyVerdict(reasons)
