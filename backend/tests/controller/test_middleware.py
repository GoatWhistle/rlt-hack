import re
from uuid import UUID

import httpx
import pytest
from starlette.types import Message, Receive, Scope, Send

from src.controller.http.middleware import RequestContextMiddleware

TIMING = re.compile(r"^app;dur=\d+\.\d$")


async def test_valid_request_id_is_echoed(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health/live", headers={"X-Request-Id": "abcDEF12-34"})
    assert response.headers["x-request-id"] == "abcDEF12-34"


@pytest.mark.parametrize("incoming", [None, "short", "bad id with spaces", "x" * 65, "abc_defgh"])
async def test_invalid_request_id_is_replaced(
    client: httpx.AsyncClient, incoming: str | None
) -> None:
    headers = {} if incoming is None else {"X-Request-Id": incoming}
    response = await client.get("/api/health/live", headers=headers)
    generated = response.headers["x-request-id"]
    assert generated != incoming
    assert UUID(generated).version == 4


async def test_request_id_reaches_error_body(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/missing", headers={"X-Request-Id": "trace-0001"})
    assert response.json()["requestId"] == "trace-0001"


async def test_server_timing_is_reported(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health/live")
    assert TIMING.match(response.headers["server-timing"])


async def test_error_responses_carry_server_timing(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/missing")
    assert TIMING.match(response.headers["server-timing"])


async def test_non_http_scopes_pass_through() -> None:
    seen: list[str] = []

    async def inner(scope: Scope, receive: Receive, send: Send) -> None:
        seen.append(scope["type"])

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(message: Message) -> None:
        return None

    await RequestContextMiddleware(inner)({"type": "lifespan"}, receive, send)
    assert seen == ["lifespan"]


async def test_docs_are_served_under_api(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/docs")).status_code == 200
    schema = (await client.get("/api/openapi.json")).json()
    assert "/api/searches" in schema["paths"]
    assert (await client.get("/docs")).status_code == 404
