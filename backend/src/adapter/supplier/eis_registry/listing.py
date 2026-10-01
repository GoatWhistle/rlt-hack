"""Выдача реестра контрактов ЕИС: адрес запроса и разбор страницы результатов.

Разметка сверена по архивным снимкам выдачи реестра контрактов (web.archive.org,
2021–2022): блоки `search-registry-entry-block`, число в `search-results__total`,
поля формы `publishDateFrom/To`. Живой сайт в проверке был недоступен.
"""

import re
from urllib.parse import parse_qs, urlencode, urlsplit

from src.adapter.supplier import page
from src.adapter.supplier.eis_registry.dto import ListingEntry, ListingPage, Slice
from src.adapter.supplier.errors import ContentFormatError

BASE_URL = "https://zakupki.gov.ru"
SEARCH_PATH = "/epz/contract/search/results.html"
PAGE_SIZE = 50
MAX_PAGES = 100
DATE_FORMAT = "%d.%m.%Y"

_DIGITS = re.compile(r"\d[\d\s\xa0]*")
_REESTR = re.compile(r"\d{10,}")
_CUSTOMER_LABELS = ("заказчик",)


def search_url(part: Slice, page_number: int) -> str:
    query = {
        "morphology": "on",
        "fz44": "on",
        "contractStageList_0": "on",
        "contractStageList_1": "on",
        "contractStageList_2": "on",
        "contractStageList_3": "on",
        "contractStageList": "0,1,2,3",
        "sortBy": "PUBLISH_DATE",
        "sortDirection": "true",
        "pageNumber": str(page_number),
        "recordsPerPage": f"_{PAGE_SIZE}",
        "publishDateFrom": part.window.start.strftime(DATE_FORMAT),
        "publishDateTo": part.window.end.strftime(DATE_FORMAT),
    }
    if part.price is not None:
        query["currencyCode"] = "RUB"
        query["contractPriceFrom"] = f"{part.price.low:.2f}"
        query["contractPriceTo"] = f"{part.price.high:.2f}"
    return f"{BASE_URL}{SEARCH_PATH}?{urlencode(query)}"


def card_page_url(card_url: str, page_name: str) -> str:
    number = reestr_number(card_url)
    return f"{BASE_URL}/epz/contract/contractCard/{page_name}.html?reestrNumber={number}"


def reestr_number(url: str) -> str | None:
    values = parse_qs(urlsplit(url).query).get("reestrNumber")
    if values and _REESTR.fullmatch(values[0]):
        return values[0]
    return None


def _text(element) -> str:
    return " ".join(element.text_content().split())


def parse_listing(text: str, url: str) -> ListingPage:
    tree = page.parse(text, url)
    total_nodes = tree.cssselect(".search-results__total")
    blocks = tree.cssselect(".search-registry-entry-block")
    if not total_nodes:
        if blocks:
            raise ContentFormatError(f"В выдаче нет общего числа результатов: {url}")
        if "не найдено" in page.document_text(tree).casefold():
            return ListingPage(0, ())
        raise ContentFormatError(f"Страница не является выдачей реестра контрактов: {url}")
    match = _DIGITS.search(_text(total_nodes[0]))
    if match is None:
        raise ContentFormatError(f"Не прочитано общее число результатов: {url}")
    total = int(re.sub(r"\D", "", match.group()))
    lower_bound = "более" in _text(total_nodes[0]).casefold()
    entries: list[ListingEntry] = []
    for block in blocks:
        anchors = block.cssselect(".registry-entry__header-mid__number a")
        if not anchors:
            raise ContentFormatError(f"У записи выдачи нет ссылки на карточку: {url}")
        card_url = anchors[0].get("href") or ""
        number = reestr_number(card_url)
        if number is None:
            raise ContentFormatError(f"В ссылке записи нет реестрового номера: {card_url}")
        titles = block.cssselect(".registry-entry__header-top__title")
        law = _text(titles[0]).split(" ", 1)[0] if titles else ""
        states = block.cssselect(".registry-entry__header-mid__title")
        entries.append(
            ListingEntry(
                reestr_number=number,
                card_url=card_url,
                law=law,
                customer=_body_value(block, _CUSTOMER_LABELS),
                status=_text(states[0]) if states else "",
            )
        )
    if total and not entries:
        raise ContentFormatError(f"Выдача сообщает {total} результатов, но записей нет: {url}")
    return ListingPage(total, tuple(entries), lower_bound)


def _body_value(block, labels: tuple[str, ...]) -> str:
    for title in block.cssselect(".registry-entry__body-title"):
        if any(label in _text(title).casefold() for label in labels):
            sibling = title.getnext()
            if sibling is not None:
                return _text(sibling)
    return ""
