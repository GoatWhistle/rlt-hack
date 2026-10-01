"""Чтение HTML-страницы: разбор документа и выборка по CSS-селекторам.

Правила разбора общие для всех адаптеров: кодировку задаёт ответ сервера,
ссылки приводятся к абсолютным, а текст документа читается без скриптов и
стилей. Разбор блокирующий и упирается в CPU, поэтому адаптер вызывает его в
пуле потоков.
"""

from typing import Any
from urllib.parse import urlsplit

from lxml import html as lxml_html

_HIDDEN_TAGS = frozenset({"script", "style", "noscript"})

# Профиль в соцсети сайтом компании не считается: он не описывает ассортимент.
SOCIAL_HOSTS = (
    "vk.com",
    "instagram.com",
    "facebook.com",
    "t.me",
    "telegram.me",
    "youtube.com",
    "ok.ru",
    "dzen.ru",
    "wa.me",
    "wa.clck.bar",
)


def parse(text: str, url: str) -> Any:
    """Кодировку задаёт ответ сервера: иначе lxml читает кириллицу как latin-1."""
    parser = lxml_html.HTMLParser(encoding="utf-8")
    tree = lxml_html.fromstring(text.encode("utf-8"), base_url=url, parser=parser)
    tree.make_links_absolute(url, resolve_base_href=True)
    return tree


def document_text(tree: Any) -> str:
    """Видимый текст страницы: скрипты, стили и комментарии в него не попадают."""
    parts: list[str] = []
    for node in tree.iter():
        if not isinstance(node.tag, str):
            continue
        if node.text and node.tag not in _HIDDEN_TAGS:
            parts.append(node.text)
        if node.tail:
            parts.append(node.tail)
    return " ".join(" ".join(parts).split())


def links(tree: Any, selector: str) -> list[str]:
    found: list[str] = []
    for element in tree.cssselect(selector):
        href = element.get("href")
        if href and href not in found:
            found.append(href)
    return found


def first_text(tree: Any, selector: str) -> str:
    for element in tree.cssselect(selector):
        text = " ".join(element.text_content().split())
        if text:
            return text
    return ""


def external_link(tree: Any, selector: str, base_url: str) -> str:
    """Первая ссылка выборки на сайт компании: свой домен и соцсети пропускаются."""
    for href in links(tree, selector):
        if is_company_site(href, base_url):
            return href
    return ""


def is_company_site(url: str, base_url: str) -> bool:
    """Адрес ведёт на сайт компании, а не внутрь источника и не в соцсеть."""
    host = urlsplit(url).netloc.removeprefix("www.")
    own = urlsplit(base_url).netloc.removeprefix("www.")
    if not host or host == own or host.endswith("." + own):
        return False
    return not any(host == social or host.endswith("." + social) for social in SOCIAL_HOSTS)
