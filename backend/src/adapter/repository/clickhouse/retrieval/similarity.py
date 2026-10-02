from collections.abc import Sequence
from dataclasses import dataclass

from src.adapter.repository.clickhouse.retrieval.terms import match_share


@dataclass(frozen=True, slots=True)
class LotSimilarity:
    match_share: float = 0.5
    win_weight: float = 2.0
    participation_weight: float = 1.0

    def __post_init__(self) -> None:
        if not 0 < self.match_share <= 1:
            raise ValueError("match share must be within (0, 1]")
        if self.win_weight <= 0 or self.participation_weight <= 0:
            raise ValueError("weights must be positive")

    def similar(self, flags: Sequence[bool]) -> bool:
        return bool(flags) and match_share(flags) >= self.match_share

    def weight(self, won: bool) -> float:
        return self.win_weight if won else self.participation_weight
