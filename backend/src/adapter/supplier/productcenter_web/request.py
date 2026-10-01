"""HTTP-запросы ProductCenter с ограниченными повторами."""

import asyncio
import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from src.adapter.supplier.errors import SourceUnavailableError
from src.adapter.supplier.productcenter_web.cache import PageCache

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
logger = logging.getLogger(__name__)


class RequestPacer:
    def __init__(self, interval_seconds: float) -> None:
        self._interval = max(0.0, interval_seconds)
        self._next_at = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        if self._interval == 0:
            return
        loop = asyncio.get_running_loop()
        async with self._lock:
            now = loop.time()
            scheduled = max(now, self._next_at)
            self._next_at = scheduled + self._interval
        await asyncio.sleep(max(0.0, scheduled - now))


async def get(
    http: httpx.AsyncClient,
    url: str,
    retries: int,
    cache: PageCache | None = None,
    *,
    connection_retries: int | None = None,
    pacer: RequestPacer | None = None,
) -> httpx.Response:
    if cache is not None:
        cached = await cache.read(url)
        if cached is not None:
            return httpx.Response(
                200,
                content=cached,
                headers={"Content-Type": "text/html; charset=utf-8"},
                request=httpx.Request("GET", url),
            )
    status_failures = 0
    connection_failures = 0
    max_connection_failures = retries if connection_retries is None else connection_retries
    while True:
        if pacer is not None:
            await pacer.wait()
        try:
            response = await http.get(url)
        except httpx.RequestError as error:
            if connection_failures >= max_connection_failures:
                raise SourceUnavailableError(f"{url}: {error}") from error
            delay = min(2 ** min(connection_failures, 5), 30)
            connection_failures += 1
            logger.warning(
                "ProductCenter %s: сетевой сбой %d/%d, повтор через %d с: %s",
                url,
                connection_failures,
                max_connection_failures,
                delay,
                error,
            )
            await asyncio.sleep(delay)
            continue
        if response.status_code in RETRY_STATUSES:
            if status_failures >= retries:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as error:
                    raise SourceUnavailableError(f"{url}: {error}") from error
            delay = _retry_after(response.headers.get("Retry-After"))
            if delay is None:
                delay = min(2 ** min(status_failures, 5), 30)
            status_failures += 1
            await asyncio.sleep(delay)
            continue
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise SourceUnavailableError(f"{url}: {error}") from error
        if cache is not None and response.status_code == 200 and response.content:
            try:
                await cache.write(url, response.content)
            except OSError as error:
                logger.warning("Кеш ProductCenter не записал %s: %s", url, error)
        return response


def _retry_after(raw: str | None) -> float | None:
    if not raw:
        return None
    if raw.isdecimal():
        return float(raw)
    try:
        return max(0.0, (parsedate_to_datetime(raw) - datetime.now(UTC)).total_seconds())
    except (ValueError, TypeError):
        return None
