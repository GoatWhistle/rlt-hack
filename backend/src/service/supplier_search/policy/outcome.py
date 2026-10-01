from dataclasses import dataclass

from src.models.enums import CandidateStatus, CheckReason


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    reason: CheckReason
    triggered: bool


@dataclass(frozen=True, slots=True)
class PolicyVerdict:
    reasons: tuple[CheckReason, ...] = ()

    @property
    def status(self) -> CandidateStatus:
        return CandidateStatus.CHECK if self.reasons else CandidateStatus.RECOMMENDED
