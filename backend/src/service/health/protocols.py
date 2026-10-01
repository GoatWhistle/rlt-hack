from typing import Protocol


class DependencyProbe(Protocol):
    @property
    def name(self) -> str: ...

    async def check(self) -> None: ...
