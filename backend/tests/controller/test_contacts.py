from dataclasses import replace

import httpx
import pytest

from src.controller.search.mapper import contacts_dto
from tests.fakes.domain import make_candidate, make_result, make_supplier
from tests.fakes.http import FakeServiceProvider, make_profile

SITES = [
    ("javascript:alert(1)", ""),
    ("JavaScript:alert(document.cookie)", ""),
    ("//evil.example", ""),
    ("www.example.ru", ""),
    ("/internal/path", ""),
    ("data:text/html,<script>alert(1)</script>", ""),
    ("ftp://files.example.ru", ""),
    ("https://", ""),
    ("", ""),
    (" https://ok.example/catalog ", "https://ok.example/catalog"),
    ("http://ok.example", "http://ok.example"),
]

EMAILS = [
    ("sales@ok.example.ru", "sales@ok.example.ru"),
    (" sales@ok.example.ru ", "sales@ok.example.ru"),
    ("sales@ok.example.ru?body=x", ""),
    ("javascript:alert(1)@x.ru", ""),
    ("not an email", ""),
    ("", ""),
]


@pytest.mark.parametrize(("raw", "expected"), SITES)
def test_contacts_site_keeps_only_web_urls(raw: str, expected: str) -> None:
    supplier = replace(make_supplier(), website=raw)
    assert contacts_dto(supplier).site == expected


@pytest.mark.parametrize(("raw", "expected"), EMAILS)
def test_contacts_email_keeps_only_plain_addresses(raw: str, expected: str) -> None:
    supplier = replace(make_supplier(), contacts={"email": raw, "phone": "+7 812"})
    contacts = contacts_dto(supplier)
    assert (contacts.email, contacts.phone) == (expected, "+7 812")


async def test_search_response_drops_unsafe_site(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    supplier = replace(make_supplier(), website="javascript:alert(1)")
    provider.searching.result = make_result(make_candidate(supplier=supplier))
    response = await client.post("/api/searches", json={"text": "рис"})
    assert response.json()["candidates"][0]["contacts"]["site"] == ""


async def test_profile_drops_unsafe_site(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    profile = make_profile()
    supplier = replace(profile.supplier, website="//evil.example")
    provider.profiles.profile = replace(profile, supplier=supplier)
    response = await client.get(f"/api/suppliers/{supplier.supplier_id}")
    assert response.json()["contacts"]["site"] == ""
