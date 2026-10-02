from dataclasses import dataclass
from datetime import datetime
from typing import Self
from uuid import UUID

from src.models.enums import CandidateStatus, ItemOrigin, LotStatus, WarningCode
from src.models.errors import InvalidLotResultError
from src.models.search_result import SearchResult

DEGRADING_WARNINGS = frozenset({WarningCode.CHANNEL_FAILED, WarningCode.ENRICHMENT_FAILED})


def search_status(result: SearchResult) -> LotStatus:
    if not result.candidates:
        return LotStatus.NO_CANDIDATES
    assumed = any(item.origin == ItemOrigin.INFERRED for item in result.items)
    leader_checked = result.candidates[0].status == CandidateStatus.CHECK
    degraded = any(warning.code in DEGRADING_WARNINGS for warning in result.warnings)
    if assumed or leader_checked or degraded:
        return LotStatus.NEEDS_CHECK
    return LotStatus.READY


@dataclass(frozen=True, slots=True)
class LotResult:
    lot_id: str
    processed_at: datetime
    status: LotStatus = LotStatus.NO_CANDIDATES
    search_id: UUID | None = None
    products: int = 0
    candidates: int = 0

    def __post_init__(self) -> None:
        if not self.lot_id:
            raise InvalidLotResultError("lot id is empty")
        if self.processed_at.tzinfo is None:
            raise InvalidLotResultError("processed_at must carry a timezone")
        if self.status == LotStatus.QUEUED:
            raise InvalidLotResultError("a processed lot is not queued")
        if self.products < 0 or self.candidates < 0:
            raise InvalidLotResultError("counters cannot be negative")
        if self.failed and (self.search_id is not None or self.products or self.candidates):
            raise InvalidLotResultError("a failed lot has no search")
        if self.candidates and self.search_id is None:
            raise InvalidLotResultError("candidates come from an archived search")
        if (self.status == LotStatus.NO_CANDIDATES) != (not self.failed and not self.candidates):
            raise InvalidLotResultError("no candidates exactly when the search found none")

    @classmethod
    def of_search(cls, lot_id: str, processed_at: datetime, result: SearchResult) -> Self:
        return cls(
            lot_id=lot_id,
            processed_at=processed_at,
            status=search_status(result),
            search_id=result.search_id,
            products=len(result.items),
            candidates=len(result.candidates),
        )

    @classmethod
    def failure(cls, lot_id: str, processed_at: datetime) -> Self:
        return cls(lot_id=lot_id, processed_at=processed_at, status=LotStatus.FAILED)

    @classmethod
    def not_understood(cls, lot_id: str, processed_at: datetime) -> Self:
        return cls(lot_id=lot_id, processed_at=processed_at)

    @property
    def failed(self) -> bool:
        return self.status == LotStatus.FAILED
