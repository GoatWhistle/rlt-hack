from typing import Protocol

from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.policy.outcome import RuleOutcome


class PolicyRule(Protocol):
    def apply(self, draft: CandidateDraft) -> RuleOutcome: ...
