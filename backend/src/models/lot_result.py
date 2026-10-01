from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.models.candidate import SupplierCandidate, ranking_problem
from src.models.enums import CandidateStatus, ItemOrigin, LotStatus, WarningCode
from src.models.errors import InvalidLotResultError
from src.models.query_item import QueryItem
from src.models.search_result import PipelineInfo, SearchWarning

DEGRADING_WARNINGS = frozenset({WarningCode.CHANNEL_FAILED, WarningCode.ENRICHMENT_FAILED})


@dataclass(frozen=True, slots=True)
class LotResult:
    lot_id: str
    processed_at: datetime
    items: tuple[QueryItem, ...] = ()
    candidates: tuple[SupplierCandidate, ...] = ()
    warnings: tuple[SearchWarning, ...] = ()
    failed: bool = False
    pipeline: PipelineInfo | None = None

    def __post_init__(self) -> None:
        if not self.lot_id:
            raise InvalidLotResultError("lot id is empty")
        if self.processed_at.tzinfo is None:
            raise InvalidLotResultError("processed_at must carry a timezone")
        if self.failed and (self.items or self.candidates):
            raise InvalidLotResultError("a failed lot has no items or candidates")
        problem = ranking_problem(self.candidates, self.items)
        if problem is not None:
            raise InvalidLotResultError(problem)

    @classmethod
    def failure(cls, lot_id: str, processed_at: datetime) -> Self:
        return cls(lot_id=lot_id, processed_at=processed_at, failed=True)

    @property
    def degraded(self) -> bool:
        return any(warning.code in DEGRADING_WARNINGS for warning in self.warnings)

    @property
    def status(self) -> LotStatus:
        if self.failed:
            return LotStatus.FAILED
        if not self.candidates:
            return LotStatus.NO_CANDIDATES
        assumed = any(item.origin == ItemOrigin.INFERRED for item in self.items)
        leader_checked = self.candidates[0].status == CandidateStatus.CHECK
        if assumed or leader_checked or self.degraded:
            return LotStatus.NEEDS_CHECK
        return LotStatus.READY
