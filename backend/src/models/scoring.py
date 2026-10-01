import math
from dataclasses import dataclass
from typing import Self

from src.models.errors import InvalidRankError, InvalidScoreError


@dataclass(frozen=True, slots=True, order=True)
class Score:
    value: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.value) or not 0.0 <= self.value <= 1.0:
            raise InvalidScoreError(self.value)

    @classmethod
    def zero(cls) -> Self:
        return cls(0.0)

    @classmethod
    def clamp(cls, value: float) -> Self:
        if not math.isfinite(value):
            return cls(0.0)
        return cls(min(1.0, max(0.0, value)))

    @classmethod
    def ratio(cls, part: float, whole: float) -> Self:
        return cls.clamp(part / whole) if whole > 0 else cls(0.0)


@dataclass(frozen=True, slots=True)
class ChannelRank:
    channel: str
    rank: int

    def __post_init__(self) -> None:
        if not self.channel:
            raise InvalidRankError("channel is empty")
        if self.rank < 1:
            raise InvalidRankError("ranks start at 1")


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    fusion: Score
    coverage: Score
    evidence: Score
    history: Score
    total: Score
    channels: tuple[ChannelRank, ...] = ()
