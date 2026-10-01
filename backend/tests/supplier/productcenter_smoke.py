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
from src.adapter.supplier.productcenter_web.request import get
from src.models.enums import SourceType, SupplierRole, VerificationStatus
from src.models.source import Source

BASE = "https://productcenter.ru"
INDEX = f"{BASE}/sitemaps/sitemaps.xml"
P1 = f"{BASE}/producers/11/first"
P2 = f"{BASE}/producers/12/second"
P3 = f"{BASE}/producers/13/without-products"
P4 = f"{BASE}/producers/14/same-inn"
G1 = f"{BASE}/products/21/one"
G2 = f"{BASE}/products/22/two"
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
            f"<a href='/{kind}/page-2'>2</a></html>"
        ).encode()
        maps[f"{root}/page-2"] = (
            f"<html><div class='card_item {card_class}'><a href='{links[1]}'>two</a></div></html>"
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
) -> ProductCenterWebProvider:
    def handler(request: httpx.Request) -> httpx.Response:
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
        cache_dir=cache_dir,
        transport=httpx.MockTransport(handler),
    )


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
    with tempfile.TemporaryDirectory() as directory:
        cache = PageCache(Path(directory))
        with patch.object(cache, "write", side_effect=OSError("disk full")):
            async with httpx.AsyncClient(transport=httpx.MockTransport(throttled)) as http:
                assert (await get(http, f"{BASE}/cache-write", 0, cache)).status_code == 200
    print("ProductCenter: package, links, UUID, duplicates, failures, limit, format OK")


if __name__ == "__main__":
    asyncio.run(check())
