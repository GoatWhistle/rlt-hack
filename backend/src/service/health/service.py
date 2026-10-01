import asyncio
import logging
from collections.abc import Sequence

from src.models.enums import ComponentState
from src.models.health import ComponentHealth, Readiness
from src.service.health.protocols import DependencyProbe

logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, probes: Sequence[DependencyProbe], timeout_seconds: float = 2.0) -> None:
        self._probes = tuple(probes)
        self._timeout = timeout_seconds

    async def readiness(self) -> Readiness:
        states = await asyncio.gather(*(self._probe(probe) for probe in self._probes))
        return Readiness(components=tuple(states))

    async def _probe(self, probe: DependencyProbe) -> ComponentHealth:
        try:
            await asyncio.wait_for(probe.check(), self._timeout)
        except Exception:
            logger.warning("dependency %s is not ready", probe.name, exc_info=True)
            return ComponentHealth(name=probe.name, state=ComponentState.DOWN)
        return ComponentHealth(name=probe.name, state=ComponentState.UP)
