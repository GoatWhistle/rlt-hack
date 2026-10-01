from typing import Protocol

from src.models.health import Readiness


class ReadinessChecking(Protocol):
    async def readiness(self) -> Readiness: ...
