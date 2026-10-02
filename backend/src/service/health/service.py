import asyncio
import logging
from collections.abc import Sequence

from src.models.enums import ComponentState
from src.models.operations.health import ComponentHealth, Readiness
from src.service.health.protocols import DependencyProbe

logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, probes: Sequence[DependencyProbe], timeout_seconds: float = 2.0) -> None:
        self._probes = tuple(probes)
        self._timeout = timeout_seconds
        self._failures: dict[str, str] = {}

    async def readiness(self) -> Readiness:
        states = await asyncio.gather(*(self._probe(probe) for probe in self._probes))
        return Readiness(components=tuple(states))

    async def _probe(self, probe: DependencyProbe) -> ComponentHealth:
        try:
            await asyncio.wait_for(probe.check(), self._timeout)
        except Exception as error:
            self._report(probe.name, error)
            return ComponentHealth(name=probe.name, state=ComponentState.DOWN)
        self._failures.pop(probe.name, None)
        return ComponentHealth(name=probe.name, state=ComponentState.UP)

    def _report(self, name: str, error: Exception) -> None:
        kind = type(error).__name__
        repeated = self._failures.get(name) == kind
        self._failures[name] = kind
        logger.warning(
            "dependency is not ready",
            extra={"dependency": name, "error_type": kind, "repeated": repeated},
            exc_info=not repeated,
        )
