from collections.abc import Sequence

from src.models.candidate import SupplierCandidate
from src.models.enums import CandidateStatus
from src.models.scoring import Score, ScoreBreakdown
from src.service.supplier_search.assembly.draft import CandidateDraft
from src.service.supplier_search.policy.outcome import PolicyVerdict
from src.service.supplier_search.ranking.components import (
    coverage_score,
    evidence_score,
    history_score,
)
from src.service.supplier_search.settings import ScoreWeights

type Judged = tuple[CandidateDraft, PolicyVerdict]


class CandidateRanker:
    def __init__(self, weights: ScoreWeights) -> None:
        self._weights = weights

    def score(self, draft: CandidateDraft) -> ScoreBreakdown:
        coverage = coverage_score(draft.matches, draft.total_items)
        evidence = evidence_score(draft.matches)
        history = history_score(draft.history)
        weights = self._weights
        weighted = (
            weights.fusion * draft.fusion.value
            + weights.coverage * coverage.value
            + weights.evidence * evidence.value
            + weights.history * history.value
        )
        return ScoreBreakdown(
            fusion=draft.fusion,
            coverage=coverage,
            evidence=evidence,
            history=history,
            total=Score.clamp(weighted / weights.total),
            channels=draft.channels,
        )

    def rank(self, judged: Sequence[Judged], limit: int) -> tuple[SupplierCandidate, ...]:
        scored = [(draft, verdict, self.score(draft)) for draft, verdict in judged]
        scored.sort(key=_order)
        return tuple(
            SupplierCandidate(
                supplier=draft.supplier,
                role=draft.role,
                status=verdict.status,
                score=score,
                rank=position,
                role_evidence=draft.role_evidence,
                check_reasons=verdict.reasons,
                matches=draft.matches,
                history=draft.history,
                highlights=draft.highlights,
            )
            for position, (draft, verdict, score) in enumerate(scored[: max(limit, 0)], start=1)
        )


type Scored = tuple[CandidateDraft, PolicyVerdict, ScoreBreakdown]


def _order(entry: Scored) -> tuple[bool, float, str, str, str]:
    draft, verdict, score = entry
    return (
        verdict.status != CandidateStatus.RECOMMENDED,
        -score.total.value,
        draft.supplier.inn or "",
        draft.supplier.name,
        str(draft.supplier_id),
    )
