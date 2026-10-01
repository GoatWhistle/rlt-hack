"""Чтение sitemap источника.

Sitemap — машинный перечень страниц, который источник публикует сам: он не
зависит от вёрстки навигации и не требует перебора пагинации. Индексы
разворачиваются рекурсивно, недоступный вложенный файл пропускается.
"""

import asyncio
import logging
from xml.etree import ElementTree

import httpx

from src.adapter.supplier.errors import SourceUnavailableError

logger = logging.getLogger(__name__)

MAX_DEPTH = 2

_NAMESPACE = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


async def read_urls(
    http: httpx.AsyncClient,
    url: str,
    depth: int = 0,
    max_depth: int = MAX_DEPTH,
) -> list[str]:
    """Адреса страниц из sitemap или его индекса.

    Недоступный корневой файл — ошибка источника: обход не начался. Сбой
    вложенного файла только пропускает его часть адресов.
    """
    if depth > max_depth:
        return []
    try:
        response = await http.get(url)
        response.raise_for_status()
    except httpx.HTTPError as error:
        if depth == 0:
            raise SourceUnavailableError(f"{url}: {error}") from error
        logger.warning("Вложенный sitemap %s не прочитан: %s", url, error)
        return []
    root = await asyncio.to_thread(_parse, response.content, url)
    urls = [
        element.text.strip()
        for element in root.findall("sm:url/sm:loc", _NAMESPACE)
        if element.text
    ]
    for nested in root.findall("sm:sitemap/sm:loc", _NAMESPACE):
        if nested.text:
            urls.extend(await read_urls(http, nested.text.strip(), depth + 1, max_depth))
    return urls


def _parse(content: bytes, url: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise SourceUnavailableError(f"{url}: XML не разобран: {error}") from error
