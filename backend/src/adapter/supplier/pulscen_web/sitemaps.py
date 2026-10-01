"""Строгое чтение дерева sitemap Пульса цен.

Пакет означает полный снимок, поэтому любая недоступная или нераспознанная часть
дерева завершает обход ошибкой. Сжатые карты `.xml.gz` распознаются по байтам:
сервер может отдать их без заголовка `Content-Encoding`.
"""

import asyncio
import gzip
from collections.abc import Awaitable, Callable
from xml.etree import ElementTree

import httpx

from src.adapter.supplier.errors import SourceUnavailableError

_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

_GZIP_MAGIC = b"\x1f\x8b"

SitemapGetter = Callable[[str], Awaitable[bytes]]

NestedFilter = Callable[[str], bool]


async def read_tree(
    get: SitemapGetter,
    url: str,
    wanted: NestedFilter,
) -> list[str]:
    """Адреса страниц из корневой карты и всех нужных вложенных карт."""
    root = await _load(get, url)
    kind = root.tag.removeprefix(_SITEMAP_NS)
    if kind == "urlset":
        return _locs(root, "url")
    if kind != "sitemapindex":
        raise SourceUnavailableError(f"{url}: корень {root.tag} не является sitemap")
    urls: list[str] = []
    for nested in _locs(root, "sitemap"):
        if wanted(nested):
            urls.extend(await read_tree(get, nested, wanted))
    return urls


async def _load(get: SitemapGetter, url: str) -> ElementTree.Element:
    try:
        content = await get(url)
    except httpx.HTTPError as error:
        raise SourceUnavailableError(f"{url}: {error}") from error
    try:
        if content[:2] == _GZIP_MAGIC:
            content = await asyncio.to_thread(gzip.decompress, content)
        return await asyncio.to_thread(ElementTree.fromstring, content)
    except (OSError, EOFError, ElementTree.ParseError) as error:
        raise SourceUnavailableError(f"{url}: sitemap не разобран: {error}") from error


def _locs(root: ElementTree.Element, tag: str) -> list[str]:
    found = [
        element.text.strip()
        for element in root.findall(f"{_SITEMAP_NS}{tag}/{_SITEMAP_NS}loc")
        if element.text
    ]
    if not found:
        raise SourceUnavailableError(f"sitemap без элементов <{tag}>")
    return found
