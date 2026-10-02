import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token

type Stages = list[tuple[str, float]]

STAGES: ContextVar[Stages | None] = ContextVar("server_timing_stages", default=None)


def bind_stages() -> Token[Stages | None]:
    return STAGES.set([])


def release_stages(token: Token[Stages | None]) -> None:
    STAGES.reset(token)


def server_timing(app_ms: float) -> str:
    entries = [("app", app_ms), *(STAGES.get() or ())]
    return ", ".join(f"{name};dur={duration:.1f}" for name, duration in entries)


class ServerTimingStages:
    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            recorded = STAGES.get()
            if recorded is not None:
                recorded.append((name, (time.perf_counter() - started) * 1000))
