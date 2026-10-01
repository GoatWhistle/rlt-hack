"""Разбор страниц Пульса цен: список товаров рубрики и каталог компаний.

Список товаров размечен JSON-LD `ItemList` с `Product` и `Offer`: название, цена
и наличие, но без продавца. Каталог компаний — карточки `li.company-card` с
идентификатором компании, названием, ролями, адресом и ссылкой на сайт. Реквизитов
(ИНН) в списках нет, поэтому они остаются неизвестными.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.adapter.supplier import jsonld, page
from src.models.enums import Availability, SupplierRole

_PRODUCT_ID = re.compile(r"_(\d+)/?$")

_COMPANY_LINK = re.compile(r"/companies/(\d+)(?:/|$)")

_NEAR_LEVELS = 5

_COMPANY_IN_TITLE = re.compile(r"от компании\s+(.+?)\s*$")

_ROLES = (
    ("Производитель", SupplierRole.MANUFACTURER),
    ("Оптовый продавец", SupplierRole.DISTRIBUTOR),
    ("Розничный продавец", SupplierRole.RESELLER),
    ("Услуги и сервис", SupplierRole.SERVICE_PROVIDER),
)

_AVAILABILITY = {
    "instock": Availability.AVAILABLE,
    "outofstock": Availability.UNAVAILABLE,
    "preorder": Availability.ON_ORDER,
    "backorder": Availability.ON_ORDER,
}


@dataclass(frozen=True, slots=True)
class ListedProduct:
    external_id: str
    url: str
    name: str
    price: Decimal | None
    currency: str
    availability: Availability


@dataclass(frozen=True, slots=True)
class ListedCompany:
    company_id: str
    name: str
    website: str
    address: str
    roles: tuple[SupplierRole, ...]


def product_id(url: str) -> str:
    """Числовой ID товара из адреса: региональные поддомены дают один и тот же ID."""
    match = _PRODUCT_ID.search(url.split("?")[0])
    return match.group(1) if match else url


def products(tree: Any) -> list[ListedProduct]:
    found: list[ListedProduct] = []
    for node in jsonld.of_types(jsonld.nodes(tree), frozenset({"ItemList"})):
        for entry in node.get("itemListElement") or ():
            item = jsonld.first(entry.get("item") if isinstance(entry, dict) else None)
            url = jsonld.text(item.get("url"))
            name = jsonld.text(item.get("name"))
            if not url or not name:
                continue
            offer = jsonld.first(item.get("offers"))
            stock = jsonld.text(offer.get("availability")).rsplit("/", 1)[-1].casefold()
            found.append(
                ListedProduct(
                    external_id=product_id(url),
                    url=url,
                    name=name,
                    price=jsonld.number(offer.get("price")),
                    currency=jsonld.text(offer.get("priceCurrency")),
                    availability=_AVAILABILITY.get(stock, Availability.UNKNOWN),
                )
            )
    return found


def companies(tree: Any) -> list[ListedCompany]:
    found: list[ListedCompany] = []
    for card in tree.cssselect("li.company-card"):
        company_id = card.get("data-id") or ""
        title = card.cssselect(".ccd-title")
        name = " ".join(title[0].text_content().split()) if title else ""
        if not company_id or not name:
            continue
        markers = " ".join(
            " ".join(m.text_content().split()) for m in card.cssselect(".ccd-marker")
        )
        found.append(
            ListedCompany(
                company_id=company_id,
                name=name,
                website=title[0].get("data-to") or "" if title else "",
                address=_address(card),
                roles=tuple(role for label, role in _ROLES if label in markers),
            )
        )
    return found


@dataclass(frozen=True, slots=True)
class ProductSeller:
    company_id: str
    name: str


def product_seller(tree: Any) -> ProductSeller | None:
    """Продавец товара по ссылке на компанию, подтверждённой названием из заголовка.

    Ссылок на компании на странице несколько: рекомендации и похожие товары тоже
    ведут на чужие компании. Продавцом считается компания, рядом со ссылкой на
    которую (в ближайших родительских блоках) стоит название из заголовка. Один
    ID без названия принимается, если других компаний на странице нет. При
    неоднозначности продавец не назначается.
    """
    title = page.first_text(tree, "title")
    named = _COMPANY_IN_TITLE.search(title)
    name = named.group(1) if named else ""
    candidates: dict[str, bool] = {}
    for link in tree.cssselect("a[href*='/companies/']"):
        match = _COMPANY_LINK.search((link.get("href") or "").split("?")[0].split("#")[0])
        if match:
            confirmed = bool(name) and _near_text(link, name)
            candidates[match.group(1)] = candidates.get(match.group(1), False) or confirmed
    confirmed_ids = [company_id for company_id, confirmed in candidates.items() if confirmed]
    if len(confirmed_ids) == 1:
        return ProductSeller(confirmed_ids[0], name)
    if not confirmed_ids and len(candidates) == 1:
        return ProductSeller(next(iter(candidates)), name)
    return None


def _near_text(link: Any, name: str) -> bool:
    wanted = " ".join(name.split()).casefold().strip('"«» ')
    for index, block in enumerate(link.iterancestors()):
        if index >= _NEAR_LEVELS or block.tag in ("body", "html"):
            return False
        if wanted in " ".join(block.text_content().split()).casefold():
            return True
    return False


def has_next_page(tree: Any) -> bool:
    return bool(tree.cssselect("link[rel='next']"))


def is_bot_check(text: str) -> bool:
    return "Проверка безопасности - Pulscen" in text


def _address(card: Any) -> str:
    for element in card.cssselect(".ccd-address .ccda-row"):
        text = " ".join(element.text_content().split())
        if text:
            return text
    return ""
