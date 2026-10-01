"""HTTP-запросы ProductCenter с ограниченными повторами."""

import asyncio
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from src.adapter.supplier.errors import SourceUnavailableError
from src.adapter.supplier.productcenter_web.cache import PageCache

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


async def get(
    http: httpx.AsyncClient,
    url: str,
    retries: int,
    cache: PageCache | None = None,
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
    for attempt in range(retries + 1):
        try:
            response = await http.get(url)
            if response.status_code not in RETRY_STATUSES:
                response.raise_for_status()
                if cache is not None and response.status_code == 200 and response.content:
                    await cache.write(url, response.content)
                return response
            if attempt == retries:
                response.raise_for_status()
            delay = _retry_after(response.headers.get("Retry-After"))
        except httpx.HTTPError as error:
            if attempt == retries or isinstance(error, httpx.HTTPStatusError):
                raise SourceUnavailableError(f"{url}: {error}") from error
            delay = None
        await asyncio.sleep(min(delay if delay is not None else 2**attempt, 30))
    raise SourceUnavailableError(f"{url}: исчерпаны повторы")


def _retry_after(raw: str | None) -> float | None:
    if not raw:
        return None
    if raw.isdecimal():
        return float(raw)
    try:
        return max(0.0, (parsedate_to_datetime(raw) - datetime.now(UTC)).total_seconds())
    except (ValueError, TypeError):
        return None
