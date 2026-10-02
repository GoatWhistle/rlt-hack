"""Доля с числителем, знаменателем и неизвестными значениями."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Ratio:
    numerator: int
    denominator: int
    unknown: int = 0

    @property
    def share(self) -> float | None:
        """При нулевом знаменателе базы для расчёта нет: это не 0 % и не 100 %."""
        return None if self.denominator == 0 else self.numerator / self.denominator


@dataclass(frozen=True, slots=True)
class CountRow:
    key: str
    count: int
