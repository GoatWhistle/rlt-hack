"""HTTP-клиент ЕИС: таймаут, ограниченные повторы, Retry-After, предел параллелизма."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from src.adapter.supplier.errors import SourceUnavailableError

logger = logging.getLogger(__name__)

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RETRY_DELAY = 60.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

Sleeper = Callable[[float], Awaitable[None]]


def retry_after(response: httpx.Response, fallback: float) -> float:
    raw = response.headers.get("Retry-After", "").strip()
    if raw.isdigit():
        return min(float(raw), MAX_RETRY_DELAY)
    if raw:
        try:
            moment = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return fallback
        return min(max((moment - datetime.now(UTC)).total_seconds(), 0.0), MAX_RETRY_DELAY)
    return fallback


class EisHttp:
    def __init__(
        self,
        client: httpx.AsyncClient,
        max_concurrent: int,
        attempts: int,
        backoff: float,
        sleep: Sleeper = asyncio.sleep,
        min_interval: float = 0.0,
    ) -> None:
        self._client = client
        self._min_interval = max(0.0, min_interval)
        self._pace = asyncio.Lock()
        self._next_start = 0.0
        self._gate = asyncio.Semaphore(max(1, max_concurrent))
        self._attempts = max(1, attempts)
        self._backoff = backoff
        self._sleep = sleep

    async def _wait_turn(self) -> None:
        if not self._min_interval:
            return
        async with self._pace:
            now = time.monotonic()
            wait = self._next_start - now
            self._next_start = max(now, self._next_start) + self._min_interval
            if wait > 0:
                await self._sleep(wait)

    async def get_text(self, url: str, allow_missing: bool = False) -> str | None:
        """Текст страницы; None только для 404 при allow_missing (снятая карточка)."""
        last_error = "нет ответа"
        for attempt in range(self._attempts):
            fallback = self._backoff * 2**attempt
            delay = fallback
            try:
                async with self._gate:
                    await self._wait_turn()
                    response = await self._client.get(url)
            except httpx.TransportError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 404 and allow_missing:
                    return None
                if response.status_code in RETRY_STATUSES:
                    last_error = f"HTTP {response.status_code}"
                    delay = retry_after(response, fallback)
                elif response.is_success:
                    return response.text
                else:
                    raise SourceUnavailableError(f"ЕИС ответил HTTP {response.status_code}: {url}")
            if attempt + 1 < self._attempts:
                logger.warning("Повтор запроса ЕИС %s: %s", url, last_error)
                await self._sleep(delay)
        raise SourceUnavailableError(f"ЕИС недоступен ({last_error}): {url}")
