from typing import Protocol


class MeasuredUnit(Protocol):
    @property
    def base(self) -> str: ...
