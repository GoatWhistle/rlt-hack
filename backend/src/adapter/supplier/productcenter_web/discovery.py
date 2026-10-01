"""Полный перечень карточек из опубликованных карт и общих списков."""

import asyncio
import gzip
import re
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

import httpx

from src.adapter.supplier.errors import ContentFormatError
from src.adapter.supplier.productcenter_web.cache import PageCache
from src.adapter.supplier.productcenter_web.request import get

BASE_URL = "https://productcenter.ru"
SITEMAP_URL = f"{BASE_URL}/sitemaps/sitemaps.xml"
_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
_PRODUCER = re.compile(r"^/producers/(\d+)/[^/]+/?$")
_PRODUCT = re.compile(r"^/products/(\d+)/[^/]+/?$")
_PAGE = re.compile(r"^/(producers|products)/page-(\d+)/?$")


def card_key(url: str, kind: str) -> str | None:
    parts = urlsplit(url)
    if parts.netloc.removeprefix("www.") != "productcenter.ru":
        return None
    match = (_PRODUCER if kind == "producers" else _PRODUCT).fullmatch(parts.path)
    return match.group(1) if match else None


def xml_locs(content: bytes, indexed: bool) -> list[str]:
    if content[:2] == b"\x1f\x8b":
        try:
            content = gzip.decompress(content)
        except OSError as error:
            raise ContentFormatError(f"Повреждённый gzip sitemap: {error}") from error
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise ContentFormatError(f"Неверная карта сайта: {error}") from error
    expected = "sitemapindex" if indexed else "urlset"
    if root.tag != f"{{{_NS['s']}}}{expected}":
        raise ContentFormatError(f"Ожидалась карта {expected}, получено {root.tag}")
    path = "s:sitemap/s:loc" if indexed else "s:url/s:loc"
    urls = [node.text.strip() for node in root.findall(path, _NS) if node.text]
    if not urls:
        raise ContentFormatError("Карта сайта пуста")
    return urls


async def sitemap_cards(
    http: httpx.AsyncClient, retries: int, cache: PageCache | None = None
) -> dict[str, dict[str, str]]:
    index = await get(http, SITEMAP_URL, retries, cache)
    try:
        names = await asyncio.to_thread(xml_locs, index.content, True)
    except ContentFormatError:
        if cache is not None:
            await cache.invalidate(SITEMAP_URL)
        raise
    pattern = re.compile(r"sitemap-(producers|products)(?:-part\d+)?\.xml\.gz$")
    selected = [u for u in names if pattern.fullmatch(urlsplit(u).path.rsplit("/", 1)[-1])]
    selected_names = {urlsplit(u).path.rsplit("/", 1)[-1] for u in selected}
    if not {"sitemap-producers.xml.gz", "sitemap-products.xml.gz"} <= selected_names:
        if cache is not None:
            await cache.invalidate(SITEMAP_URL)
        raise ContentFormatError("В индексе отсутствует карта компаний или товаров")
    cards: dict[str, dict[str, str]] = {"producers": {}, "products": {}}
    for url in selected:
        response = await get(http, url, retries, cache)
        try:
            urls = await asyncio.to_thread(xml_locs, response.content, False)
        except ContentFormatError:
            if cache is not None:
                await cache.invalidate(url)
            raise
        kind = "producers" if "producers" in urlsplit(url).path else "products"
        for card_url in urls:
            key = card_key(card_url, kind)
            if key:
                cards[kind].setdefault(key, card_url)
    if not all(cards.values()):
        raise ContentFormatError("В картах нет карточек производителей или товаров")
    return cards


def listing_links(tree: object, kind: str) -> tuple[dict[str, str], int]:
    found: dict[str, str] = {}
    last = 1
    card_class = "firm" if kind == "producers" else "product"
    for node in tree.cssselect(f".card_item.{card_class} a[href]"):
        url = urljoin(BASE_URL, node.get("href"))
        key = card_key(url, kind)
        if key:
            found.setdefault(key, url)
    for node in tree.xpath("//a[@href]"):
        url = urljoin(BASE_URL, node.get("href"))
        match = _PAGE.fullmatch(urlsplit(url).path)
        if match and match.group(1) == kind:
            last = max(last, int(match.group(2)))
    if not found:
        raise ContentFormatError(f"Список {kind} не содержит карточек")
    return found, last
