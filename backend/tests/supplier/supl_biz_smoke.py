"""Проверка адаптера Supl.biz на искусственных документах и подменённом HTTP.

Запуск: `uv run --no-project --python 3.13 --with httpx python tests/supplier/supl_biz_smoke.py`
из каталога `backend`. Живой сайт не используется.
"""

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.supplier import identity
from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.supl_biz_web import PROVIDER_NAME, SuplBizWebProvider
from src.models.enums import Availability, ItemType, SourceType
from src.models.source import Source

SITEMAP = "https://supl.biz/sitemap.xml"
PART_1 = "https://supl.biz/sitemap-proposals.xml"
PART_2 = "https://supl.biz/sitemap-proposals.xml?p=2"
USERS = "https://supl.biz/sitemap-users.xml"
PROFILE_10 = "https://supl.biz/profile-10/"
PROFILE_30 = "https://supl.biz/profile-30/"
PROFILE_GONE = "https://supl.biz/profile-99/"
FIRST = "https://supl.biz/prodam-gvozdi-p1/"
SECOND = "https://supl.biz/prodam-doski-p2/"
GONE = "https://supl.biz/udalyonnyj-p3/"
NO_PRICE = "https://supl.biz/dogovornaya-p4/"
INN = "5401359011"
OWN_INN = "5249107304"
KPP = "540101001"


def index(*parts: str) -> str:
    entries = "".join(f"<sitemap><loc>{part}</loc></sitemap>" for part in parts)
    return f'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</sitemapindex>'


def urlset(*urls: str) -> str:
    entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</urlset>'


def card(proposal_id: int, seller_id: int, title: str, price: str | None, inn: str | None) -> str:
    state = {
        "proposal": {
            "proposal": {
                "data": {
                    "id": proposal_id,
                    "title": title,
                    "description": "Описание товара",
                    "price": price,
                    "currency": "RUB",
                    "availability": 1,
                    "priceDetails": "Цена за 1 кг",
                    "specification": {"specificationsWithoutSplit": "ГОСТ 283-75"},
                    "breadcrumbs": [{"id": 1, "name": "Стройматериалы"}],
                    "categories": [{"id": 2, "name": "Крепёж"}],
                }
            },
            "supplier": {
                "data": {
                    "id": seller_id,
                    "name": f"Продавец {seller_id}, ООО",
                    "phone": "83832674455",
                    "address": "Есенина, 3",
                    "origin": {"title": "Новосибирск"},
                    "inn": inn,
                }
            },
        }
    }
    body = json.dumps(state, ensure_ascii=False)
    script = f'<script id="preloadedState" type="application/json">{body}</script>'
    return f"<html><body>{script}</body></html>"


def profile(seller_id: int, title: str, inn: str | None, kpp: str | None) -> str:
    state = {
        "profile": {
            "data": {
                "id": seller_id,
                "title": title,
                "origin": {"title": "Мытищи"},
                "phone": "+79689788877",
                "email": "info@example.ru",
                "site": "http://www.example.ru/",
                "company": {"summary": "Производство"},
            }
        },
        "requisites": {"data": {"inn": inn, "kpp": kpp, "ogrn": "1125476104269"}},
    }
    body = json.dumps(state, ensure_ascii=False)
    script = f'<script id="preloadedState" type="application/json">{body}</script>'
    return f"<html><body>{script}</body></html>"


def pages() -> dict[str, str]:
    return {
        SITEMAP: index(PART_1, PART_2, USERS),
        USERS: urlset(PROFILE_10, PROFILE_30, PROFILE_GONE),
        PROFILE_10: profile(10, "Продавец 10, ООО", INN, KPP),
        PROFILE_30: profile(30, "Компания без товаров", OWN_INN, None),
        PART_1: urlset(FIRST, SECOND, GONE),
        PART_2: urlset(FIRST, NO_PRICE),
        FIRST: card(1, 10, "Гвозди", "28.00", INN),
        SECOND: card(2, 10, "Доски", "350", INN),
        NO_PRICE: card(4, 20, "Услуга по договорённости", "0.00", None),
    }


def transport(documents: dict[str, str], failing: tuple[str, ...] = ()) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url in failing:
            return httpx.Response(500, text="сбой источника")
        body = documents.get(url)
        if body is None:
            return httpx.Response(404, text="нет страницы")
        return httpx.Response(200, text=body)

    return httpx.MockTransport(handler)


def make(documents: dict[str, str], **options) -> SuplBizWebProvider:
    source = Source(
        source_id=identity.source_id("https://supl.biz/", PROVIDER_NAME),
        name="Supl.biz",
        base_url="https://supl.biz/",
        source_type=SourceType.DIRECTORY,
        provider_name=PROVIDER_NAME,
    )
    return SuplBizWebProvider(source, retries=0, transport=transport(documents, **options))


async def check_package() -> None:
    package = await make(pages()).fetch()
    assert len(package.offers) == 3, "повтор URL и удалённая страница не дают лишних записей"
    assert len(package.suppliers) == 3, "компания без товаров собрана из профиля"
    by_name = {offer.name: offer for offer in package.offers}
    nails = by_name["Гвозди"]
    assert nails.price == Decimal("28.00") and nails.currency == "RUB"
    assert nails.availability is Availability.AVAILABLE
    assert nails.source_category == "Стройматериалы", "путь — только цепочка breadcrumbs"
    assert nails.attributes["categories"] == "Крепёж", "прочие категории не склеиваются"
    assert nails.attributes["specification"] == "ГОСТ 283-75"
    assert by_name["Услуга по договорённости"].price is None, "нулевая цена — не указана"
    ids = {supplier.supplier_id: supplier for supplier in package.suppliers}
    assert all(offer.supplier_id in ids for offer in package.offers)
    seller = ids[nails.supplier_id]
    assert seller.inn == INN and seller.region == "Мытищи"
    assert seller.identity_evidence_url == "https://supl.biz/profile-10/"
    assert seller.supplier_id == identity.supplier_id(INN, package.source.source_id, "x")
    assert seller.kpps == (KPP,) and seller.website == "http://www.example.ru/"
    assert seller.contacts["email"] == "info@example.ru" and seller.contacts["phone"]
    unknown = ids[by_name["Услуга по договорённости"].supplier_id]
    assert unknown.inn is None
    assert {offer.item_type for offer in package.offers} == {ItemType.UNKNOWN}
    assert any(s.inn == OWN_INN and s.name == "Компания без товаров" for s in package.suppliers)


async def check_category_spam() -> None:
    spam = card(5, 10, "Шины", "10", INN)
    state = json.loads(spam.split('application/json">')[1].split("</script>")[0])
    data = state["proposal"]["proposal"]["data"]
    data["breadcrumbs"] = []
    data["categories"] = [{"id": n, "name": f"Категория {n}"} for n in range(14)]
    body = json.dumps(state, ensure_ascii=False)
    script = f'<script id="preloadedState" type="application/json">{body}</script>'
    documents = pages() | {FIRST: f"<html><body>{script}</body></html>"}
    package = await make(documents).fetch()
    tires = next(o for o in package.offers if o.name == "Шины")
    assert tires.source_category == "Категория 0", "без breadcrumbs берётся одна категория"
    assert tires.attributes["categories"].split(" | ")[0] == "Категория 1"
    assert len(tires.attributes["categories"].split(" | ")) == 13


async def check_repeat() -> None:
    first = await make(pages()).fetch()
    second = await make(pages()).fetch()
    assert {o.offer_id: o.content_hash for o in first.offers} == {
        o.offer_id: o.content_hash for o in second.offers
    }
    assert {s.supplier_id for s in first.suppliers} == {s.supplier_id for s in second.suppliers}


async def check_failures() -> None:
    empty = pages() | {PART_1: urlset(), PART_2: urlset()}
    await expect(make(empty).fetch(), SourceUnavailableError)
    await expect(make({SITEMAP: index(USERS)}).fetch(), SourceUnavailableError)
    await expect(make({SITEMAP: index(PART_1)}).fetch(), SourceUnavailableError)
    maintenance = "<html><body>Maintenance</body></html>"
    for broken_part in (PART_2, PART_1, USERS):
        await expect(make(pages() | {broken_part: maintenance}).fetch(), SourceUnavailableError)
    await expect(make(pages() | {PART_2: "<urlset></urlset>"}).fetch(), SourceUnavailableError)
    foreign = urlset("https://evil.example/x/")
    await expect(make(pages() | {PART_2: foreign}).fetch(), SourceUnavailableError)
    await expect(make(pages() | {PROFILE_30: "<html></html>"}).fetch(), ContentFormatError)
    await expect(make(pages(), failing=(PROFILE_30,)).fetch(), SourceUnavailableError)
    await expect(make({SITEMAP: "не xml"}).fetch(), SourceUnavailableError)
    await expect(make({}).fetch(), SourceUnavailableError)
    broken = pages() | {FIRST: "<html><body>без состояния</body></html>"}
    await expect(make(broken).fetch(), ContentFormatError)
    await expect(make(pages(), failing=(SECOND,)).fetch(), SourceUnavailableError)
    await expect(make(pages(), failing=(PART_2,)).fetch(), SourceUnavailableError)


async def check_limit() -> None:
    limited = SuplBizWebProvider(
        make(pages()).source, max_cards=3, retries=0, transport=transport(pages())
    )
    await expect(limited.fetch(), ContentFormatError)
    sample = await limited.sample(2)
    assert len(sample.offers) == 2


async def expect(call, error: type[Exception]) -> None:
    try:
        await call
    except error:
        return
    raise AssertionError(f"ожидалась ошибка {error.__name__}")


async def main() -> None:
    await check_package()
    await check_category_spam()
    await check_repeat()
    await check_failures()
    await check_limit()
    print("Проверка адаптера Supl.biz пройдена")


if __name__ == "__main__":
    asyncio.run(main())
