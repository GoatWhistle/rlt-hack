import httpx
import pytest

from src.controller.http.locale import parse_accept_language
from src.models.enums import Locale
from tests.fakes.http import FakeServiceProvider


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, Locale.RU),
        ("", Locale.RU),
        ("en", Locale.EN),
        ("EN-gb", Locale.EN),
        ("ru-RU,ru;q=0.9", Locale.RU),
        ("de,en;q=0.8,ru;q=0.5", Locale.EN),
        ("ru;q=0.4, en;q=0.9", Locale.EN),
        ("en;q=0, ru;q=0.1", Locale.RU),
        ("en;q=abc", Locale.RU),
        ("fr, de", Locale.RU),
        ("*", Locale.RU),
        ("en;level=1;q=0.7, ru;q=0.6", Locale.EN),
        ("ru, en", Locale.RU),
        (",,", Locale.RU),
    ],
)
def test_accept_language_is_parsed(header: str | None, expected: Locale) -> None:
    assert parse_accept_language(header) == expected


async def test_locale_reaches_the_service(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    await client.post("/api/searches", json={"text": "рис"}, headers={"Accept-Language": "en"})
    await client.post("/api/searches", json={"text": "рис"})
    assert [query.locale for query in provider.searching.queries] == [Locale.EN, Locale.RU]
