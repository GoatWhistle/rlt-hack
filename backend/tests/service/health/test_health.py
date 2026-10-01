import logging
from dataclasses import dataclass

import pytest

from src.models.enums import ComponentState
from src.service.health.service import HealthService


@dataclass(slots=True)
class FlakyProbe:
    error: Exception | None = None

    @property
    def name(self) -> str:
        return "clickhouse"

    async def check(self) -> None:
        if self.error is not None:
            raise self.error


async def test_repeated_failure_logs_stack_once(caplog: pytest.LogCaptureFixture) -> None:
    probe = FlakyProbe(ConnectionError("refused"))
    service = HealthService((probe,))
    with caplog.at_level(logging.WARNING):
        for _ in range(3):
            readiness = await service.readiness()
            assert readiness.components[0].state == ComponentState.DOWN
        probe.error = None
        assert (await service.readiness()).ready
        probe.error = ConnectionError("refused again")
        await service.readiness()
    stacks = [bool(record.exc_info) for record in caplog.records]
    assert stacks == [True, False, False, True]
    assert {vars(record)["error_type"] for record in caplog.records} == {"ConnectionError"}
