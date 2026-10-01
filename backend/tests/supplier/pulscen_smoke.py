"""Проверка адаптера Пульс цен на подготовленных документах без сети."""

import asyncio
import gzip
import json
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.supplier import identity, page
from src.adapter.supplier.errors import (
    BotProtectionError,
    ContentFormatError,
    SourceUnavailableError,
)
from src.adapter.supplier.pulscen_web import PulscenSnapshotProvider, PulscenWebProvider, parsing
from src.models.enums import Availability, ItemType, SourceType, SupplierRole
from tests.supplier.fixtures import (
    PULSCEN_BOT_CHECK,
    PULSCEN_CARD_AMBIGUOUS,
    PULSCEN_CARD_FOREIGN_LINK,
    PULSCEN_CARD_LINK_IN_BODY,
    PULSCEN_CARD_REVIEWS_LINK,
    PULSCEN_CARD_WITH_RECOMMENDATIONS,
    PULSCEN_FIRMS_PAGE,
    PULSCEN_FIRMS_PAGE_2,
    PULSCEN_PRICE_PAGE,
    PULSCEN_PRODUCT_CARD,
    PULSCEN_PRODUCT_CARD_NEW_SELLER,
    PULSCEN_SITEMAP_FIRMS,
    PULSCEN_SITEMAP_INDEX,
    PULSCEN_SITEMAP_PRICE,
    SITEMAP_GOODS,
)
from tests.supplier.provider_smoke import source, transport

BASE = "https://www.pulscen.ru"

PAGES = {
    f"{BASE}/sitemap.xml": PULSCEN_SITEMAP_INDEX,
    f"{BASE}/sitemap_firms_rubrics.xml.gz": PULSCEN_SITEMAP_FIRMS,
    f"{BASE}/sitemap_price_1.xml.gz": PULSCEN_SITEMAP_PRICE,
    "https://nsk.pulscen.ru/products/armatura_a3_14mm_185531520": PULSCEN_PRODUCT_CARD,
    f"{BASE}/products/armatura_zapros_185531999": PULSCEN_PRODUCT_CARD_NEW_SELLER,
    f"{BASE}/firms/010301-armatura": PULSCEN_FIRMS_PAGE,
    f"{BASE}/firms/010301-armatura?page=2": PULSCEN_FIRMS_PAGE_2,
    f"{BASE}/price/010301-armatura": PULSCEN_PRICE_PAGE,
}


def provider(pages: dict[str, str], failing: tuple[str, ...] = ()) -> PulscenWebProvider:
    directory = source("Пульс цен", f"{BASE}/", SourceType.DIRECTORY, "pulscen_web")
    return PulscenWebProvider(directory, delay_seconds=0, transport=transport(pages, failing))


def gzipped_transport(pages: dict[str, str]) -> httpx.MockTransport:
    """Карты `.xml.gz` отдаются сжатыми байтами без заголовка Content-Encoding."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        body = pages.get(url)
        if body is None:
            return httpx.Response(404, text="нет страницы")
        content = gzip.compress(body.encode()) if url.endswith(".gz") else body.encode()
        return httpx.Response(200, content=content)

    return httpx.MockTransport(handler)


async def expect(error: type[Exception], pages: dict[str, str], failing: tuple[str, ...] = ()):
    try:
        await provider(pages, failing).fetch()
    except error:
        return
    raise AssertionError(f"ожидалась ошибка {error.__name__}")


async def check_snapshot() -> None:
    snapshot = {
        "companies": {
            "99418958": {
                "n": "ПервоСтрой, ООО",
                "w": "https://p.example",
                "a": "г. Новосибирск",
                "r": ["Производитель", "Оптовый продавец"],
            },
        },
        "products": {
            "185531520": {
                "n": "Арматура А400",
                "p": 68.55,
                "c": "RUB",
                "a": "InStock",
                "u": "nsk.pulscen.ru/products/armatura_185531520",
            },
            "185531999": {
                "n": "Арматура по запросу",
                "p": None,
                "c": "",
                "a": "",
                "u": "https://www.pulscen.ru/products/zapros_185531999",
            },
        },
    }
    directory = source("Снимок", f"{BASE}/", SourceType.DIRECTORY, "pulscen_snapshot")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "snapshot.json"
        path.write_text(json.dumps(snapshot, ensure_ascii=False))
        package = await PulscenSnapshotProvider(directory, path).fetch()
        again = await PulscenSnapshotProvider(directory, path).fetch()
        assert len(package.suppliers) == 1 and len(package.offers) == 2
        priced = next(o for o in package.offers if o.external_id == "185531520")
        assert priced.price == Decimal("68.55") and priced.url.startswith("https://nsk.")
        assert priced.availability == Availability.AVAILABLE
        assert [o.offer_id for o in again.offers] == [o.offer_id for o in package.offers]
        path.write_text("{}")
        for error in (ContentFormatError,):
            try:
                await PulscenSnapshotProvider(directory, path).fetch()
            except error:
                continue
            raise AssertionError("ожидалась ошибка формата снимка")
        path.write_text(json.dumps({"companies": {}, "products": {}}))
        try:
            await PulscenSnapshotProvider(directory, path).fetch()
        except ContentFormatError:
            pass
        else:
            raise AssertionError("пустой снимок должен завершаться ошибкой")
    try:
        await PulscenSnapshotProvider(directory, Path("/nonexistent/x.json")).fetch()
    except SourceUnavailableError:
        pass
    else:
        raise AssertionError("отсутствующий файл должен завершаться ошибкой")


async def main() -> None:
    package = await provider(PAGES).fetch()
    names = sorted(supplier.name for supplier in package.suppliers)
    assert names == ["АМК-Групп", "ПервоСтрой, ООО", "Сталь-Опт"], names
    first = next(s for s in package.suppliers if s.name == "ПервоСтрой, ООО")
    assert first.website == "https://pervostroi.example"
    assert first.region == "г. Новосибирск, ул. Ватутина, 99"
    assert first.inn is None
    assert len(package.offers) == 2
    priced = next(o for o in package.offers if o.external_id == "185531520")
    assert priced.price == Decimal("68.55") and priced.currency == "RUB"
    assert priced.availability == Availability.AVAILABLE
    assert priced.supplier_role == SupplierRole.UNKNOWN
    assert priced.supplier_id == first.supplier_id
    unpriced = next(o for o in package.offers if o.external_id == "185531999")
    assert unpriced.price is None and unpriced.availability == Availability.UNKNOWN
    new_seller = next(s for s in package.suppliers if s.name == "Сталь-Опт")
    assert unpriced.supplier_id == new_seller.supplier_id
    ids = {s.supplier_id for s in package.suppliers}
    assert all(o.supplier_id in ids for o in package.offers)
    expected = identity.offer_content_hash(
        name=priced.name, item_type=str(ItemType.GOODS), attributes=priced.attributes
    )
    assert priced.content_hash == expected

    tree = page.parse(PULSCEN_CARD_WITH_RECOMMENDATIONS, f"{BASE}/p")
    seller = parsing.product_seller(tree)
    assert seller == parsing.ProductSeller("10", "Верный продавец"), seller
    ambiguous = parsing.product_seller(page.parse(PULSCEN_CARD_AMBIGUOUS, f"{BASE}/p"))
    assert ambiguous is None, ambiguous
    foreign = parsing.product_seller(page.parse(PULSCEN_CARD_FOREIGN_LINK, f"{BASE}/p"))
    assert foreign is None, foreign
    reviews = parsing.product_seller(page.parse(PULSCEN_CARD_REVIEWS_LINK, f"{BASE}/p"))
    assert reviews == parsing.ProductSeller("99682156", "Региональный Склад"), reviews
    in_body = parsing.product_seller(page.parse(PULSCEN_CARD_LINK_IN_BODY, f"{BASE}/p"))
    assert in_body == parsing.ProductSeller("10", "Верный продавец"), in_body

    pages = {**PAGES, f"{BASE}/sitemap_firms_rubrics.xml.gz": PULSCEN_SITEMAP_FIRMS}
    directory = source("Пульс цен", f"{BASE}/", SourceType.DIRECTORY, "pulscen_web")
    zipped = await PulscenWebProvider(
        directory, delay_seconds=0, transport=gzipped_transport(pages)
    ).fetch()
    assert len(zipped.offers) == 2 and len(zipped.suppliers) == 3

    repeated = await provider(PAGES).fetch()
    assert sorted(o.offer_id for o in repeated.offers) == sorted(o.offer_id for o in package.offers)
    assert sorted(s.supplier_id for s in repeated.suppliers) == sorted(
        s.supplier_id for s in package.suppliers
    )

    await expect(SourceUnavailableError, {f"{BASE}/sitemap.xml": SITEMAP_GOODS})
    without_nested = {k: v for k, v in PAGES.items() if "sitemap_price_1" not in k}
    await expect(SourceUnavailableError, without_nested)
    maintenance = "<html><body>Maintenance</body></html>"
    await expect(SourceUnavailableError, {**PAGES, f"{BASE}/sitemap_price_1.xml.gz": maintenance})
    without_card = {k: v for k, v in PAGES.items() if "185531999" not in k}
    await expect(SourceUnavailableError, without_card)
    await expect(SourceUnavailableError, {f"{BASE}/sitemap.xml": "не xml"})
    await expect(SourceUnavailableError, PAGES, failing=(f"{BASE}/price/010301-armatura",))
    await expect(
        SourceUnavailableError,
        {**PAGES, f"{BASE}/firms/010301-armatura?page=2": PULSCEN_FIRMS_PAGE},
    )
    await expect(BotProtectionError, {**PAGES, f"{BASE}/firms/010301-armatura": PULSCEN_BOT_CHECK})
    await check_snapshot()
    print("Проверка адаптера Пульс цен пройдена")


if __name__ == "__main__":
    asyncio.run(main())
