from dataclasses import replace

import httpx
import pytest

from src.models.enums import Availability
from tests.fakes.domain import make_offer, make_offer_evidence, make_supplier, uid
from tests.fakes.http import FakeServiceProvider

SUPPLIER_ID = str(make_supplier().supplier_id)


async def test_profile_is_returned(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/suppliers/{SUPPLIER_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == SUPPLIER_ID
    assert body["identity"] == "verified"
    assert body["role"] == "distributor"
    assert body["contacts"]["site"] == "https://alpha.example.org"
    offer = body["offers"][0]
    assert offer["price"] == "84.50"
    assert offer["availability"] == "available"
    assert offer["source"]["kind"] == "price"
    assert offer["source"]["checkedAt"] == "2026-09-29T08:00:00Z"


async def test_offer_without_price_or_web_url(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    supplier = replace(make_supplier(), inn=None, website="", contacts={})
    offer = replace(
        make_offer(supplier=supplier, price=None, availability=Availability.ON_ORDER),
        url="not a url",
    )
    provider.profiles.profile = replace(
        provider.profiles.profile,
        supplier=supplier,
        offers=(make_offer_evidence(offer),),
        role_evidence=None,
    )
    body = (await client.get(f"/api/suppliers/{SUPPLIER_ID}")).json()
    assert body["inn"] == ""
    assert body["roleSource"] is None
    assert body["contacts"] == {"site": "", "email": "", "phone": ""}
    assert body["offers"][0]["price"] is None
    assert body["offers"][0]["source"] is None
    assert body["offers"][0]["availability"] == "on_order"


async def test_unknown_supplier_is_not_found(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/suppliers/{uid('nobody')}")
    assert response.status_code == 404
    assert response.json()["code"] == "supplier_not_found"


@pytest.mark.parametrize("supplier_id", ["nope", "42"])
async def test_invalid_supplier_id_is_not_found(
    client: httpx.AsyncClient, supplier_id: str
) -> None:
    response = await client.get(f"/api/suppliers/{supplier_id}")
    assert response.status_code == 404
    assert response.json()["code"] == "supplier_not_found"
