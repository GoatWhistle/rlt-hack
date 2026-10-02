"""ProductCenter: полный снимок и отказ от частичного результата."""

import asyncio
import gzip
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.supplier import identity
from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.productcenter_web import ProductCenterWebProvider
from src.adapter.supplier.productcenter_web.cache import PageCache
from src.adapter.supplier.productcenter_web.request import RequestPacer, get
from src.models.catalog.source import Source
from src.models.enums import SourceType, SupplierRole, VerificationStatus

BASE = "https://productcenter.ru"
INDEX = f"{BASE}/sitemaps/sitemaps.xml"
P1 = f"{BASE}/producers/11/first"
P2 = f"{BASE}/producers/12/second"
P3 = f"{BASE}/producers/13/without-products"
P4 = f"{BASE}/producers/14/same-inn"
G1 = f"{BASE}/products/21/one"
G2 = f"{BASE}/products/22/two"
G3 = f"{BASE}/products/23/three"
MAPS = {
    "sitemap-producers.xml.gz": [P1, P2, P3, P4, P1],
    "sitemap-products.xml.gz": [G1],
    "sitemap-products-part2.xml.gz": [G2, G1],
}


def xml(root: str, urls: list[str]) -> bytes:
    item = "sitemap" if root == "sitemapindex" else "url"
    body = "".join(f"<{item}><loc>{url}</loc></{item}>" for url in urls)
    return f'<{root} xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</{root}>'.encode()


def pages() -> dict[str, bytes]:
    maps = {
        f"{BASE}/sitemaps/{name}": gzip.compress(xml("urlset", urls)) for name, urls in MAPS.items()
    }
    maps[INDEX] = xml("sitemapindex", list(maps))
    for kind, links in (("producers", [P1, P2]), ("products", [G1, G2])):
        root = f"{BASE}/{kind}"
        card_class = "firm" if kind == "producers" else "product"
        maps[root] = (
            f"<html><div class='card_item {card_class}'><a href='{links[0]}'>one</a></div>"
            "<div class='pagination'><ul class='page_links'>"
            "<li><span class='pl_mark'>1</span></li>"
            f"<li><a href='/{kind}/page-2'>2</a></li></ul></div></html>"
        ).encode()
        maps[f"{root}/page-2"] = (
            f"<html><head><title>Список | Страница 2</title></head>"
            f"<div class='card_item {card_class}'><a href='{links[1]}'>two</a></div>"
            "</html>"
        ).encode()
    for url, name, inn in (
        (P1, "Первый завод", "7804428656"),
        (P2, "Второй завод", ""),
        (P3, "Без товаров", ""),
        (P4, "Первый завод филиал", "7804428656"),
    ):
        data = {
            "@type": "Organization",
            "name": name,
            "taxID": inn,
            "address": {"addressRegion": "Москва"},
        }
        maps[url] = (
            f"<html><h1>{name}</h1>"
            f'<script type="application/ld+json">{json.dumps(data)}</script></html>'
        ).encode()
    for url, owner in ((G1, P1), (G2, P2)):
        data = {
            "@type": "Product",
            "name": "Товар",
            "description": "Описание",
            "offers": {
                "price": "100",
                "priceCurrency": "RUB",
                "availability": "https://schema.org/InStock",
            },
        }
        maps[url] = (
            f'<html><h1>Товар</h1><script type="application/ld+json">{json.dumps(data)}</script>'
            '<div class="iv_features"><table><tr><td>35</td><td>КГ</td></tr></table></div>'
            f'<div class="contact_firm_id"><a href="{owner}">Завод</a></div></html>'
        ).encode()
    return maps


def provider(
    data: dict[str, bytes],
    max_cards: int | None = None,
    cache_dir: Path | None = None,
    delayed_url: str | None = None,
) -> ProductCenterWebProvider:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == delayed_url:
            await asyncio.sleep(0.03)
        body = data.get(str(request.url))
        return httpx.Response(200, content=body) if body is not None else httpx.Response(503)

    source = Source(
        identity.source_id(BASE, "productcenter_web"),
        "ПродуктЦентр",
        BASE,
        SourceType.DIRECTORY,
        "productcenter_web",
    )
    return ProductCenterWebProvider(
        source,
        max_concurrent=2,
        retries=0,
        max_cards=max_cards,
        request_interval=0,
        cache_dir=cache_dir,
        transport=httpx.MockTransport(handler),
    )


async def no_wait(_seconds: float) -> None:
    return None


async def check() -> None:
    data = pages()
    adapter = provider(data)
    first = await adapter.fetch()
    second = await provider(data).fetch()
    assert len(first.suppliers) == 3
    assert len(first.offers) == 2
    assert any(s.name == "Без товаров" for s in first.suppliers)
    assert {s.supplier_id for s in first.suppliers} == {s.supplier_id for s in second.suppliers}
    assert {o.offer_id for o in first.offers} == {o.offer_id for o in second.offers}
    assert {o.supplier_id for o in first.offers} <= {s.supplier_id for s in first.suppliers}
    assert all(o.supplier_role == SupplierRole.MANUFACTURER for o in first.offers)
    assert all(o.seller_status == VerificationStatus.VERIFIED for o in first.offers)
    assert all(o.attributes["Характеристика 1"] == "35 КГ" for o in first.offers)
    assert any(s.inn == "7804428656" for s in first.suppliers)
    assert adapter.stats["discovered_producers"] == 4
    assert adapter.stats["discovered_products"] == 2
    assert adapter.stats["read_supplier_card"] == 4
    assert adapter.stats["read_product_card"] == 2
    with tempfile.TemporaryDirectory() as directory:
        cache_dir = Path(directory)
        cached_first = await provider(data, cache_dir=cache_dir).fetch()
        cached_second_adapter = provider({}, cache_dir=cache_dir)
        cached_second = await cached_second_adapter.fetch()
        assert {o.offer_id for o in cached_first.offers} == {
            o.offer_id for o in cached_second.offers
        }
        assert cached_second_adapter.stats["cache_hits"] > 0
    for broken in (P1, G1, f"{BASE}/products/page-2", f"{BASE}/sitemaps/sitemap-products.xml.gz"):
        partial = data.copy()
        del partial[broken]
        try:
            await provider(partial).fetch()
        except (SourceUnavailableError, ExceptionGroup):
            pass
        else:
            raise AssertionError(f"Неполный обход был опубликован: {broken}")
    try:
        await provider(data, max_cards=5).fetch()
    except ContentFormatError:
        pass
    else:
        raise AssertionError("Диагностический лимит вернул неполный пакет")
    empty_map = data.copy()
    empty_map[f"{BASE}/sitemaps/sitemap-products.xml.gz"] = xml("urlset", [])
    try:
        await provider(empty_map).fetch()
    except ContentFormatError:
        pass
    else:
        raise AssertionError("Пустая карта товаров вернула пакет")
    empty = data.copy()
    empty[G1] = b"<html></html>"
    try:
        await provider(empty).fetch()
    except ExceptionGroup:
        pass
    else:
        raise AssertionError("Неверный формат товара был опубликован")
    technical = data.copy()
    technical[P1] = b"<html><h1>Checking browser</h1></html>"
    try:
        await provider(technical).fetch()
    except ExceptionGroup:
        pass
    else:
        raise AssertionError("Служебная страница была опубликована как компания")
    repeated = data.copy()
    repeated[f"{BASE}/products/page-2"] = data[f"{BASE}/products"]
    try:
        await provider(repeated).fetch()
    except ContentFormatError:
        pass
    else:
        raise AssertionError("Повтор первой страницы списка был опубликован")
    with tempfile.TemporaryDirectory() as directory:
        cache_dir = Path(directory)
        try:
            await provider(repeated, cache_dir=cache_dir).fetch()
        except ContentFormatError:
            pass
        else:
            raise AssertionError("Повтор страницы попал в кеш как полный список")
        assert len((await provider(data, cache_dir=cache_dir).fetch()).offers) == 2
    same_ids = data.copy()
    same_ids[f"{BASE}/products/page-2"] = data[f"{BASE}/products/page-2"].replace(
        G2.encode(), G1.encode()
    )
    try:
        await provider(same_ids).fetch()
    except ContentFormatError:
        pass
    else:
        raise AssertionError("Повтор набора товаров был опубликован")
    out_of_order = data.copy()
    out_of_order[f"{BASE}/products"] = (
        f"<html><div class='card_item product'><a href='{G1}'>one</a></div>"
        "<div class='pagination'><ul class='page_links'>"
        "<li><span class='pl_mark'>1</span></li>"
        "<li><a href='/products/page-3'>3</a></li></ul></div></html>"
    ).encode()
    out_of_order[f"{BASE}/products/page-2"] = (
        f"<html><div class='card_item product'><a href='{G2}'>two</a></div>"
        "<div class='pagination'><ul class='page_links'>"
        "<li><span class='pl_mark'>2</span></li>"
        "<li><a href='/products/page-3'>3</a></li></ul></div></html>"
    ).encode()
    out_of_order[f"{BASE}/products/page-3"] = (
        "<html><head><title>Список | Страница 3</title></head>"
        f"<div class='card_item product'><a href='{G3}'>three</a></div></html>"
    ).encode()
    out_of_order[G3] = data[G2]
    result = await provider(out_of_order, delayed_url=f"{BASE}/products/page-2").fetch()
    assert {offer.external_id for offer in result.offers} == {"21", "22", "23"}
    attempts = 0

    def throttled(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, text="ok")

    async with httpx.AsyncClient(transport=httpx.MockTransport(throttled)) as http:
        assert (await get(http, f"{BASE}/retry", 1)).text == "ok"
    assert attempts == 2
    refused = 0

    async def temporarily_unavailable(request: httpx.Request) -> httpx.Response:
        nonlocal refused
        if str(request.url) == G1 and refused < 6:
            refused += 1
            raise httpx.ConnectError("connection refused", request=request)
        body = data.get(str(request.url))
        return httpx.Response(200, content=body) if body is not None else httpx.Response(503)

    recovering = ProductCenterWebProvider(
        provider(data).source,
        max_concurrent=1,
        retries=5,
        transport=httpx.MockTransport(temporarily_unavailable),
    )
    with patch("src.adapter.supplier.productcenter_web.request.asyncio.sleep", no_wait):
        assert len((await recovering.fetch()).offers) == 2
    assert refused == 6
    permanent_attempts = 0

    def always_refused(request: httpx.Request) -> httpx.Response:
        nonlocal permanent_attempts
        permanent_attempts += 1
        raise httpx.ConnectError("connection refused", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(always_refused)) as http:
        with patch("src.adapter.supplier.productcenter_web.request.asyncio.sleep", no_wait):
            try:
                await get(http, f"{BASE}/unavailable", 0, connection_retries=1)
            except SourceUnavailableError:
                pass
            else:
                raise AssertionError("Постоянный сетевой отказ не остановил обход")
    assert permanent_attempts == 2
    request_times: list[float] = []

    def record_start(_request: httpx.Request) -> httpx.Response:
        request_times.append(asyncio.get_running_loop().time())
        return httpx.Response(200, text="ok")

    async with httpx.AsyncClient(transport=httpx.MockTransport(record_start)) as http:
        pacer = RequestPacer(0.01)
        await asyncio.gather(
            get(http, f"{BASE}/paced-1", 0, pacer=pacer),
            get(http, f"{BASE}/paced-2", 0, pacer=pacer),
        )
    assert request_times[1] - request_times[0] >= 0.009
    with tempfile.TemporaryDirectory() as directory:
        cache = PageCache(Path(directory))
        with patch.object(cache, "write", side_effect=OSError("disk full")):
            async with httpx.AsyncClient(transport=httpx.MockTransport(throttled)) as http:
                assert (await get(http, f"{BASE}/cache-write", 0, cache)).status_code == 200
    print("ProductCenter: package, links, UUID, duplicates, failures, limit, format OK")


if __name__ == "__main__":
    asyncio.run(check())
