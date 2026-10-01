import asyncio
import itertools
import re
import statistics
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

import httpx

SEARCH_PATH = "/api/searches"
APP_TIMING = re.compile(r"app;dur=([0-9.]+)")


@dataclass(slots=True)
class Sample:
    latency_ms: float
    status: int
    app_ms: float | None


@dataclass(slots=True)
class Mode:
    name: str
    concurrency: int
    samples: list[Sample] = field(default_factory=list)
    elapsed_s: float = 0.0


def _percentile(values: Sequence[float], share: int) -> float:
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[share - 1]


def summary(mode: Mode) -> dict[str, object]:
    ok = [sample.latency_ms for sample in mode.samples if sample.status == httpx.codes.CREATED]
    app = [sample.app_ms for sample in mode.samples if sample.app_ms is not None]
    statuses = Counter(str(sample.status) for sample in mode.samples)
    result: dict[str, object] = {
        "mode": mode.name,
        "concurrency": mode.concurrency,
        "requests": len(mode.samples),
        "errors": len(mode.samples) - len(ok),
        "statuses": dict(statuses),
        "elapsed_s": round(mode.elapsed_s, 2),
        "rps": round(len(mode.samples) / mode.elapsed_s, 2) if mode.elapsed_s else 0.0,
    }
    if ok:
        result |= {f"p{share}_ms": round(_percentile(ok, share), 1) for share in (50, 95, 99)}
        result |= {"mean_ms": round(statistics.fmean(ok), 1), "max_ms": round(max(ok), 1)}
    if app:
        result["app_p50_ms"] = round(_percentile(app, 50), 1)
    return result


async def _one(client: httpx.AsyncClient, text: str) -> Sample:
    started = time.perf_counter()
    try:
        response = await client.post(SEARCH_PATH, json={"text": text, "limit": 20})
    except httpx.HTTPError:
        return Sample((time.perf_counter() - started) * 1000, 0, None)
    latency = (time.perf_counter() - started) * 1000
    timing = APP_TIMING.search(response.headers.get("server-timing", ""))
    return Sample(latency, response.status_code, float(timing.group(1)) if timing else None)


async def run(
    client: httpx.AsyncClient, texts: Sequence[str], name: str, concurrency: int, total: int
) -> Mode:
    mode = Mode(name, concurrency)
    queue: asyncio.Queue[str] = asyncio.Queue()
    for text in itertools.islice(itertools.cycle(texts), total):
        queue.put_nowait(text)

    async def worker() -> None:
        while not queue.empty():
            mode.samples.append(await _one(client, queue.get_nowait()))

    started = time.perf_counter()
    await asyncio.gather(*(worker() for _ in range(concurrency)))
    mode.elapsed_s = time.perf_counter() - started
    return mode


async def wait_ready(client: httpx.AsyncClient, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            response = await client.get("/api/health/ready")
            if response.status_code == httpx.codes.OK:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(1)
    raise TimeoutError("API is not ready")
