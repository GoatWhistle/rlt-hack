from typing import Protocol


class DependencyProbe(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def required(self) -> bool: ...

    async def check(self) -> None: ...
