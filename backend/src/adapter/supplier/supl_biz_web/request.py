"""HTTP-запросы Supl.biz с ограниченными повторами и учётом Retry-After."""

import asyncio
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from src.adapter.supplier.errors import SourceUnavailableError

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
GONE_STATUSES = frozenset({404, 410})
# Лимит запросов источник отдаёт без Retry-After: пауза растёт с каждой попыткой.
BASE_DELAY = 5.0
MAX_DELAY = 120.0


async def get(http: httpx.AsyncClient, url: str, retries: int) -> httpx.Response | None:
    """Читает страницу; для удалённой страницы (404, 410) возвращает None."""
    for attempt in range(retries + 1):
        delay: float | None = None
        try:
            response = await http.get(url)
            if response.status_code in GONE_STATUSES:
                return None
            if response.status_code not in RETRY_STATUSES:
                response.raise_for_status()
                return response
            if attempt == retries:
                response.raise_for_status()
            delay = _retry_after(response.headers.get("Retry-After"))
        except httpx.HTTPError as error:
            if attempt == retries or isinstance(error, httpx.HTTPStatusError):
                raise SourceUnavailableError(f"{url}: {error}") from error
        await asyncio.sleep(min(delay if delay is not None else BASE_DELAY * 2**attempt, MAX_DELAY))
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
