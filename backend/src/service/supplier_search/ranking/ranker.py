from collections.abc import Sequence
from dataclasses import replace

from src.models.candidate import Highlight, SupplierCandidate
from src.models.enums import CandidateStatus, HighlightCode
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

    def rank(
        self, judged: Sequence[Judged], limit: int, preferred_region: str = ""
    ) -> tuple[SupplierCandidate, ...]:
        scored = []
        for original, verdict in judged:
            draft = original
            score = self.score(draft)
            if preferred_region and draft.supplier.registered_region == preferred_region:
                score = replace(
                    score, total=Score.clamp(score.total.value + 0.05 * (1 - score.total.value))
                )
                draft = replace(
                    draft, highlights=(*draft.highlights, Highlight(HighlightCode.SAME_REGION))
                )
            scored.append((draft, verdict, score))
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
