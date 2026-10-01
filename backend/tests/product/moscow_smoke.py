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
        return [page async for page in provider.listing_pages()]


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
    assert await _collect([{"count": 0, "items": []}]) == []

    halves = await _collect(
        [
            {"count": 4, "items": [{"id": 1, "name": "Один"}, {"id": 2, "name": "Два"}]},
            {"count": 4, "items": [{"id": 4, "name": "Четыре"}, {"id": 3, "name": "Три"}]},
        ]
    )
    assert [item.external_id for page in halves for item in page.items] == ["1", "2", "4", "3"]

    order_calls: list[dict[str, object]] = []

    def ordered(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.url.params["queryFilter"])
        order_calls.append(query)
        ids = (1, 2) if len(order_calls) == 1 else (4, 3)
        items = [{"id": i, "name": "Товар"} for i in ids]
        return httpx.Response(200, json={"count": 4, "items": items})

    async with httpx.AsyncClient(transport=httpx.MockTransport(ordered)) as client:
        provider = MoscowProductProvider(uuid4(), page_size=2, client=client)
        assert len([page async for page in provider.listing_pages()]) == 2
    assert [call["order"][0]["desc"] for call in order_calls] == [False, True]

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

    requested: list[str] = []

    def card_response(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if request.url.path.endswith("/QueryIndex"):
            return httpx.Response(200, json={"count": 1, "items": [{"id": 7, "name": "Товар"}]})
        if request.url.path.endswith("/GetSku"):
            return httpx.Response(
                200,
                json={
                    "id": 7,
                    "name": "Товар",
                    "companyId": 123,
                    "avgPrice": 99,
                    "productionDirectoryId": 9,
                    "productionDirectoryTreePathId": ".1.9.",
                    "production": {"code": "01.04", "okpd": {"code": "20.13.01"}},
                    "okeiShortName": "шт",
                    "manufacturerName": "Завод",
                    "oksmName": "Россия",
                    "skuCharacteristics": [
                        {
                            "productCharacteristicValue": {
                                "productCharacteristicName": "Масса",
                                "productCharacteristicUnitDesignationNational": "кг",
                            },
                            "characteristicValueDecimalValue": 2.5,
                        }
                    ],
                    "images": [{"fileStorageId": 42}],
                },
            )
        if request.url.path.endswith("/GetDirectoryLightChain"):
            return httpx.Response(
                200, json=[{"id": 1, "name": "Товары"}, {"id": 9, "name": "Лист"}]
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(card_response)) as client:
        provider = MoscowProductProvider(uuid4(), client=client)
        product_pages = [page async for page in provider.pages()]
        product_page = product_pages[0]
    product = product_page.items[0]
    assert product.item_type == "goods"
    assert product.category_path == ("Товары", "Лист")
    assert product.classifier_codes == {"production": "01.04", "okpd2": "20.13.01"}
    assert product.attributes == {"Масса": "2.5 кг"}
    assert product.image_urls == ("https://zakupki.mos.ru/newapi/api/FileStorage/Download?id=42",)
    assert product.unit == "шт" and product.manufacturer == "Завод" and product.country == "Россия"
    assert product.name == "Товар" and product.detail_status == "full"
    assert "companyId" not in product.raw_json and "avgPrice" not in product.raw_json
    assert len(requested) == 3

    def forbidden_card(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/QueryIndex"):
            return httpx.Response(
                200,
                json={
                    "count": 1,
                    "items": [
                        {
                            "id": 8,
                            "name": "Старая СТЕ",
                            "productionDirectoryPath": ".2.9.",
                            "productionCode": "02.01",
                            "skuImageIds": [11],
                        }
                    ],
                },
            )
        return httpx.Response(403)

    async with httpx.AsyncClient(transport=httpx.MockTransport(forbidden_card)) as client:
        provider = MoscowProductProvider(uuid4(), client=client)
        restricted_pages = [page async for page in provider.pages()]
        restricted = restricted_pages[0].items[0]
    assert restricted.detail_status == "summary_only"
    assert restricted.name == "Старая СТЕ" and restricted.item_type == "work"
    assert restricted.classifier_codes == {"production": "02.01"}
    assert restricted.image_urls[0].endswith("id=11")

    for responses, error_type in (
        ([{"count": 1, "items": [{"id": 1}]}], MoscowProductFormatError),
        (
            [
                {"count": 3, "items": [{"id": 1, "name": "Один"}, {"id": 2, "name": "Два"}]},
                {"count": 3, "items": [{"id": 2, "name": "Два"}]},
            ],
            MoscowProductIncompleteError,
        ),
        (
            [
                {"count": 4, "items": [{"id": 1, "name": "Один"}, {"id": 2, "name": "Два"}]},
                {"count": 4, "items": [{"id": 3, "name": "Три"}, {"id": 2, "name": "Два"}]},
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
    async for _ in provider.listing_pages():
        pass


if __name__ == "__main__":
    asyncio.run(main())
