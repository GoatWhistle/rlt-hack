"""Строгое чтение sitemap Supl.biz.

Файл принимается только как `sitemapindex` или `urlset` в пространстве имён
sitemap, с непустым перечнем адресов самого источника. Служебный ответ с кодом
200 (заглушка, страница обслуживания) корректным XML не перестаёт быть, поэтому
одной проверки синтаксиса недостаточно: иначе часть каталога молча пропадёт из
полного снимка.
"""

from urllib.parse import urlsplit
from xml.etree import ElementTree

from src.adapter.supplier.errors import SourceUnavailableError

INDEX = "sitemapindex"
URLSET = "urlset"
HOST_SUFFIX = "supl.biz"

_NAMESPACE = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
_ENTRY = {INDEX: "sitemap", URLSET: "url"}


def locations(content: bytes, url: str, kind: str) -> list[str]:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise SourceUnavailableError(f"{url}: XML не разобран: {error}") from error
    if root.tag != f"{_NAMESPACE}{kind}":
        raise SourceUnavailableError(f"{url}: ожидался документ {kind}, получен {root.tag}")
    found: list[str] = []
    for entry in root.findall(f"{_NAMESPACE}{_ENTRY[kind]}"):
        location = entry.find(f"{_NAMESPACE}loc")
        text = (location.text or "").strip() if location is not None else ""
        host = urlsplit(text).hostname or ""
        if not text or not (host == HOST_SUFFIX or host.endswith(f".{HOST_SUFFIX}")):
            raise SourceUnavailableError(f"{url}: некорректный адрес в перечне: {text!r}")
        found.append(text)
    if not found:
        raise SourceUnavailableError(f"{url}: в документе {kind} нет адресов")
    return found
