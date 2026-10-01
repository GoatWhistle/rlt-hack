"""Проверка контракта публичного списка СТЕ на искусственных ответах."""

import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.product.moscow.errors import (
    MoscowProductFormatError,
    MoscowProductIncompleteError,
)
from src.adapter.product.moscow.parse import product_id
from src.adapter.product.moscow.provider import MoscowProductProvider


async def _collect(responses: list[dict[str, object]]) -> list[object]:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=responses.pop(0))

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        provider = MoscowProductProvider(uuid4(), page_size=2, client=client)
        return [page async for page in provider.pages()]


async def main() -> None:
    pages = await _collect(
        [
            {"count": 3, "items": [{"id": 1, "name": "Один"}, {"id": 2, "name": "Два"}]},
            {"count": 3, "items": [{"id": 3, "name": "Три"}]},
        ]
    )
    assert [len(page.items) for page in pages] == [2, 1]
    assert product_id(pages[0].items[0].source_id, "1") == pages[0].items[0].product_id
    assert pages[0].items[0].url.endswith("/1")
    assert await _collect([{"count": 0, "items": []}]) == [pages[0].__class__(0, ())]

    requests: list[dict[str, object]] = []

    def inspect(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.url.params["queryFilter"]))
        return httpx.Response(200, json={"count": 0, "items": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(inspect)) as client:
        await _consume(MoscowProductProvider(uuid4(), page_size=2, client=client))
    assert requests == [
        {"skip": 0, "take": 2, "withCount": True, "order": [{"field": "id", "desc": False}]}
    ]

    attempts = 0

    def transient(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503 if attempts == 1 else 200, json={"count": 0, "items": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(transient)) as client:
        await _consume(MoscowProductProvider(uuid4(), client=client))
    assert attempts == 2

    for responses, error_type in (
        ([{"count": 1, "items": [{"id": 1}]}], MoscowProductFormatError),
        (
            [
                {"count": 3, "items": [{"id": 1, "name": "Один"}, {"id": 2, "name": "Два"}]},
                {"count": 3, "items": [{"id": 2, "name": "Два"}]},
            ],
            MoscowProductIncompleteError,
        ),
    ):
        try:
            await _collect(responses)
        except error_type:
            pass
        else:
            raise AssertionError(f"ожидалась {error_type.__name__}")

    def network_failure(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("сеть недоступна", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(network_failure)) as client:
        try:
            await _consume(MoscowProductProvider(uuid4(), client=client))
        except httpx.ConnectError:
            pass
        else:
            raise AssertionError("сетевой сбой был проигнорирован")


async def _consume(provider: MoscowProductProvider) -> None:
    async for _ in provider.pages():
        pass


if __name__ == "__main__":
    asyncio.run(main())
