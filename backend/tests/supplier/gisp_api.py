"""Проверка полного обхода публичных JSON-страниц ГИСП на подменённом HTTP."""

import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.supplier import identity
from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.gisp_registry import GispRegistryProvider
from src.models.enums import SourceType, SupplierRole
from src.models.source import Source

BASE = "https://gisp.gov.ru/pp719v2/pub/prod/"
SOURCE = Source(
    identity.source_id(BASE, "gisp_registry"), "ГИСП", BASE, SourceType.REGISTRY, "gisp_registry"
)
ORGANIZATIONS = [
    {
        "org_name": "ООО Завод",
        "org_inn": "7707083893",
        "org_ogrn": "1027700132195",
        "org_region_name": "Москва",
        "gisp_url": "https://gisp.gov.ru/company-catalog/company/1/",
    },
    {
        "org_name": "ООО Без ассортимента",
        "org_inn": "4707019370",
        "org_region_name": "Ленинградская область",
        "gisp_url": "https://gisp.gov.ru/company-catalog/company/2/",
    },
]
PRODUCTS = [
    {
        "_org_name": "ООО Завод",
        "_org_inn": "7707083893",
        "_gisp_url": "https://gisp.gov.ru/company-catalog/company/1/",
        "_product_reg_number_2023": str(10000000 + index),
        "_product_name": f"Станок {index}",
        "_product_okpd2": "28.41.21.110",
        "_res_date": "2026-01-01",
        "_res_valid_till": "2028-01-01",
        "_res_end_date": "2026-09-01" if index == 100 else None,
        "_basedondoc_num": f"СТ-{index}",
    }
    for index in range(101)
]


def provider(fail_last: bool = False, repeat_last: bool = False) -> GispRegistryProvider:
    def response(request: httpx.Request) -> httpx.Response:
        kind = "org" if "/org/" in request.url.path else "prod"
        option = json.loads(request.content)["opt"]
        if fail_last and kind == "prod" and option["skip"] == 100:
            return httpx.Response(200, json={"ok": True, "items": []})
        rows = ORGANIZATIONS if kind == "org" else PRODUCTS
        items = rows[option["skip"] : option["skip"] + option["take"]]
        if repeat_last and kind == "prod" and option["skip"] == 100:
            items = [rows[0]]
        data = {"ok": True, "items": items}
        if option["requireTotalCount"]:
            data["total_count"] = len(rows)
        return httpx.Response(200, json=data)

    return GispRegistryProvider(SOURCE, "", transport=httpx.MockTransport(response))


async def checks() -> None:
    first = await provider().fetch()
    again = await provider().fetch()
    assert len(first.suppliers) == 2
    assert len(first.offers) == 101
    assert {offer.offer_id for offer in first.offers} == {offer.offer_id for offer in again.offers}
    assert {offer.supplier_id for offer in first.offers} == {first.suppliers[0].supplier_id}
    assert first.suppliers[0].region == "Москва"
    assert first.offers[0].supplier_role == SupplierRole.MANUFACTURER
    assert first.offers[-1].supplier_role == SupplierRole.UNKNOWN
    assert first.offers[0].price is None
    versions = [
        PRODUCTS[0] | {"_res_scan_url": "https://gisp.gov.ru/document/1"},
        PRODUCTS[0] | {"_res_scan_url": "https://gisp.gov.ru/document/2"},
    ]

    def version_response(request: httpx.Request) -> httpx.Response:
        option = json.loads(request.content)["opt"]
        rows = ORGANIZATIONS if "/org/" in request.url.path else versions
        data = {"ok": True, "items": rows[option["skip"] : option["skip"] + option["take"]]}
        if option["requireTotalCount"]:
            data["total_count"] = len(rows)
        return httpx.Response(200, json=data)

    version_package = await GispRegistryProvider(
        SOURCE, "", transport=httpx.MockTransport(version_response)
    ).fetch()
    assert len(version_package.offers) == 2
    assert version_package.offers[0].offer_id != version_package.offers[1].offer_id
    versions = [
        PRODUCTS[0]
        | {
            "_res_scan_url": "https://gisp.gov.ru/document/1",
            "_product_writeout_url": f"https://gisp.gov.ru/app/{index}/writeout",
        }
        for index in (1, 2)
    ]
    writeout_package = await GispRegistryProvider(
        SOURCE, "", transport=httpx.MockTransport(version_response)
    ).fetch()
    assert len(writeout_package.offers) == 2
    assert writeout_package.offers[0].offer_id != writeout_package.offers[1].offer_id
    try:
        await provider(fail_last=True).fetch()
    except ContentFormatError:
        pass
    else:
        raise AssertionError("Неполная страница не должна сохранять пакет")
    try:
        await provider(repeat_last=True).fetch()
    except ContentFormatError as error:
        assert "повтор записи" in str(error)
    else:
        raise AssertionError("Повтор страницы не должен сохранять неполный пакет")
    html = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            text="<js-challenge-loader></js-challenge-loader>",
        )
    )
    try:
        await GispRegistryProvider(SOURCE, "", transport=html).fetch()
    except SourceUnavailableError as error:
        assert "HTML-проверка доступа" in str(error)
    else:
        raise AssertionError("HTML-проверка доступа не должна сохранять пакет")


if __name__ == "__main__":
    asyncio.run(checks())
    print("ГИСП API: проверки прошли")
