from dataclasses import dataclass
from datetime import datetime
from typing import Self

from src.models.candidate import SupplierCandidate
from src.models.enums import CandidateStatus, ItemOrigin, LotStatus
from src.models.errors import InvalidLotResultError
from src.models.query_item import QueryItem
from src.models.search_result import SearchWarning


@dataclass(frozen=True, slots=True)
class LotResult:
    lot_id: str
    processed_at: datetime
    items: tuple[QueryItem, ...] = ()
    candidates: tuple[SupplierCandidate, ...] = ()
    warnings: tuple[SearchWarning, ...] = ()
    failed: bool = False

    def __post_init__(self) -> None:
        if not self.lot_id:
            raise InvalidLotResultError("lot id is empty")
        if self.processed_at.tzinfo is None:
            raise InvalidLotResultError("processed_at must carry a timezone")
        if self.failed and (self.items or self.candidates):
            raise InvalidLotResultError("a failed lot has no items or candidates")
        ranks = [candidate.rank for candidate in self.candidates]
        if ranks != list(range(1, len(ranks) + 1)):
            raise InvalidLotResultError("candidate ranks must run 1..n in order")
        known = {item.item_id for item in self.items}
        if any(not candidate.matched_item_ids <= known for candidate in self.candidates):
            raise InvalidLotResultError("a match points to an unknown item")

    @classmethod
    def failure(cls, lot_id: str, processed_at: datetime) -> Self:
        return cls(lot_id=lot_id, processed_at=processed_at, failed=True)

    @property
    def status(self) -> LotStatus:
        if self.failed:
            return LotStatus.FAILED
        if not self.candidates:
            return LotStatus.NO_CANDIDATES
        assumed = any(item.origin == ItemOrigin.INFERRED for item in self.items)
        leader_checked = self.candidates[0].status == CandidateStatus.CHECK
        return LotStatus.NEEDS_CHECK if assumed or leader_checked else LotStatus.READY
