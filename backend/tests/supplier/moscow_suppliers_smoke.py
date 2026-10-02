"""Проверки полного экспорта оферт Портала поставщиков Москвы без сети."""

import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.supplier import identity
from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.moscow_suppliers import MoscowSuppliersProvider
from src.models.catalog.source import Source
from src.models.enums import SourceType

URL = "https://example.test/export"
SOURCE = Source(
    source_id=identity.source_id("https://zakupki.mos.ru/", "moscow_suppliers"),
    name="Портал поставщиков Москвы",
    base_url="https://zakupki.mos.ru/",
    source_type=SourceType.DIRECTORY,
    provider_name="moscow_suppliers",
)


def page(next_page=None):
    return {
        "complete": True,
        "snapshot_id": "export-1",
        "totals": {"suppliers": 1, "offers": 1},
        "suppliers": [
            {
                "id": "seller-7",
                "name": "Поставщик",
                "inn": "7707083893",
                "url": "https://zakupki.mos.ru/suppliers/7",
            }
        ],
        "offers": [
            {
                "id": "offer-4",
                "supplier_id": "seller-7",
                "sku_id": "sku-9",
                "name": "Кабель",
                "url": "https://zakupki.mos.ru/offers/4",
                "price": "100.50",
                "article": "141741",
                "delivery_regions": ["г Москва", "Белгородская область"],
                "delivery_days_min": "1",
                "delivery_days_max": "3",
                "valid_from": "2026-09-10",
                "valid_to": "2026-11-16",
            }
        ],
        "next": next_page,
    }


def provider(payload=None, status=200, error=False):
    def respond(request):
        if error:
            raise httpx.ConnectError("network", request=request)
        return httpx.Response(status, text=json.dumps(payload if payload is not None else page()))

    return MoscowSuppliersProvider(SOURCE, URL, transport=httpx.MockTransport(respond))


async def expect_error(adapter, error_type):
    try:
        await adapter.fetch()
    except error_type:
        return
    raise AssertionError(f"Ожидалась ошибка {error_type.__name__}")


async def run():
    adapter = provider()
    first = await adapter.fetch()
    second = await adapter.fetch()
    assert len(first.suppliers) == len(first.offers) == 1
    assert first.offers[0].supplier_id == first.suppliers[0].supplier_id
    assert first.offers[0].attributes["sku_id"] == "sku-9"
    assert first.offers[0].attributes["delivery_days_max"] == "3"
    assert first.offers[0].article == "141741"
    assert first.offers[0].attributes["delivery_regions"] == ("г Москва|Белгородская область")
    assert first.offers[0].offer_id == second.offers[0].offer_id
    assert first.offers[0].content_hash == second.offers[0].content_hash
    await expect_error(provider({**page(), "offers": []}), ContentFormatError)
    bad_regions = {**page()["offers"][0], "delivery_regions": "г Москва"}
    await expect_error(provider({**page(), "offers": [bad_regions]}), ContentFormatError)
    await expect_error(provider({**page(), "complete": False}), ContentFormatError)
    unknown_seller = {**page()["offers"][0], "supplier_id": "other"}
    await expect_error(provider({**page(), "offers": [unknown_seller]}), ContentFormatError)
    await expect_error(provider(error=True), SourceUnavailableError)
    await expect_error(provider(status=500), SourceUnavailableError)
    await expect_error(provider({**page(), "next": URL}), ContentFormatError)
    pages = {URL: {**page(), "totals": {"suppliers": 1, "offers": 2}, "next": "?page=2"}}
    pages[URL + "?page=2"] = {
        **page(),
        "totals": {"suppliers": 1, "offers": 2},
        "suppliers": [],
        "offers": [{**page()["offers"][0], "id": "offer-5"}],
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=pages[str(request.url)])
    )
    multi = MoscowSuppliersProvider(SOURCE, URL, transport=transport)
    assert len((await multi.fetch()).offers) == 2
    pages[URL + "?page=2"]["snapshot_id"] = "export-2"
    await expect_error(multi, ContentFormatError)
    out_of_order = {
        URL: {
            **page("?page=2"),
            "suppliers": [],
        },
        URL + "?page=2": {
            **page(),
            "offers": [],
        },
    }
    unordered_transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=out_of_order[str(request.url)])
    )
    unordered = MoscowSuppliersProvider(SOURCE, URL, transport=unordered_transport)
    result = await unordered.fetch()
    assert result.offers[0].supplier_id == result.suppliers[0].supplier_id
    print("moscow_suppliers_smoke: ok")


if __name__ == "__main__":
    asyncio.run(run())
