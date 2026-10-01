import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-Id"
SERVER_TIMING_HEADER = "Server-Timing"
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{8,64}")

logger = logging.getLogger(__name__)


def accepted_request_id(value: str | None) -> str | None:
    if value is not None and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return None


def request_id_of(connection: HTTPConnection) -> str:
    value = getattr(connection.state, "request_id", None)
    return value if isinstance(value, str) else ""


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        request_id = accepted_request_id(incoming) or str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        await self._app(scope, receive, send_with_id)


class ServerTimingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        started = time.perf_counter()

        async def send_with_timing(message: Message) -> None:
            if message["type"] == "http.response.start":
                elapsed = (time.perf_counter() - started) * 1000
                MutableHeaders(scope=message)[SERVER_TIMING_HEADER] = f"app;dur={elapsed:.1f}"
                logger.info(
                    "request completed",
                    extra={
                        "method": scope["method"],
                        "path": scope["path"],
                        "status": message["status"],
                        "duration_ms": round(elapsed, 1),
                        "request_id": scope.get("state", {}).get("request_id", ""),
                    },
                )
            await send(message)

        await self._app(scope, receive, send_with_timing)
