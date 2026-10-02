import json
import logging
import re
import time
from dataclasses import dataclass, field
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.controller.http.middleware.correlation import bind_request_id, release_request_id
from src.controller.http.middleware.metrics import Metrics
from src.controller.http.middleware.timing import bind_stages, release_stages, server_timing
from src.controller.http.response.error_body import INTERNAL_STATUS, internal_body

REQUEST_ID_HEADER = "X-Request-Id"
SERVER_TIMING_HEADER = "Server-Timing"
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9-]{8,64}")
UNMATCHED_ROUTE = "unmatched"

logger = logging.getLogger(__name__)


def accepted_request_id(value: str | None) -> str | None:
    if value is not None and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return None


def request_id_of(connection: HTTPConnection) -> str:
    value = getattr(connection.state, "request_id", None)
    return value if isinstance(value, str) else ""


def route_of(scope: Scope) -> str:
    path = getattr(scope.get("route"), "path", None)
    return path if isinstance(path, str) else UNMATCHED_ROUTE


@dataclass(slots=True)
class Exchange:
    request_id: str
    started: float = field(default_factory=time.perf_counter)
    status: int = INTERNAL_STATUS
    responded: bool = False

    @property
    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.started) * 1000


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, metrics: Metrics | None = None) -> None:
        self._app = app
        self._metrics = metrics or Metrics()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        exchange = Exchange(accepted_request_id(incoming) or str(uuid4()))
        scope.setdefault("state", {})["request_id"] = exchange.request_id
        token = bind_request_id(exchange.request_id)
        stages = bind_stages()

        async def reply(message: Message) -> None:
            if message["type"] == "http.response.start":
                exchange.responded = True
                exchange.status = message["status"]
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = exchange.request_id
                headers[SERVER_TIMING_HEADER] = server_timing(exchange.elapsed_ms)
            await send(message)

        try:
            await self._app(scope, receive, reply)
        except Exception:
            logger.exception(
                "unhandled error",
                extra={"request_id": exchange.request_id, "path": scope["path"]},
            )
            if not exchange.responded:
                await self._internal_error(exchange, reply)
        finally:
            self._complete(scope, exchange)
            release_stages(stages)
            release_request_id(token)

    async def _internal_error(self, exchange: Exchange, reply: Send) -> None:
        body = json.dumps(internal_body(exchange.request_id)).encode("utf-8")
        await reply(
            {
                "type": "http.response.start",
                "status": INTERNAL_STATUS,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await reply({"type": "http.response.body", "body": body})

    def _complete(self, scope: Scope, exchange: Exchange) -> None:
        elapsed = exchange.elapsed_ms
        route = route_of(scope)
        logger.info(
            "request completed",
            extra={
                "method": scope["method"],
                "path": scope["path"],
                "route": route,
                "status": exchange.status,
                "duration_ms": round(elapsed, 1),
                "request_id": exchange.request_id,
            },
        )
        labels = {"method": scope["method"], "route": route}
        self._metrics.count("http_requests_total", {**labels, "status": str(exchange.status)})
        self._metrics.count("http_request_duration_seconds_sum", labels, elapsed / 1000)
        self._metrics.count("http_request_duration_seconds_count", labels)
