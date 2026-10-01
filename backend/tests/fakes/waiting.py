import asyncio
from collections.abc import Awaitable, Callable

STEP_SECONDS = 0.01
STEPS = 300


async def eventually(check: Callable[[], Awaitable[bool]]) -> None:
    for _ in range(STEPS):
        if await check():
            return
        await asyncio.sleep(STEP_SECONDS)
    raise AssertionError("condition was not reached in time")
