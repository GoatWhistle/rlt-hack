"""Разбор страницы предложения Supl.biz.

Страница отдаётся уже собранной и содержит JSON `preloadedState`: в нём лежат
данные товара и продавца, включая опубликованный ИНН. Разметка вёрстки для
разбора не нужна. DTO внешнего формата остаются здесь и в `models` не попадают.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from src.adapter.supplier import identity
from src.adapter.supplier.errors import ContentFormatError
from src.adapter.supplier.inn import normalize_inn, normalize_kpp
from src.models.enums import Availability, ItemType, VerificationStatus
from src.models.offer import Offer
from src.models.supplier import Supplier

BASE_URL = "https://supl.biz"

MAX_OTHER_CATEGORIES = 20

_STATE = re.compile(
    r'<script id="preloadedState" type="application/json">\s*(.*?)</script>', re.DOTALL
)

# Страница не отличает товар от услуги, поэтому тип позиции остаётся неизвестным.
# Коды наличия подтверждены подписями на страницах: 1 — «В наличии», 2 — «Под заказ».
_AVAILABILITY = {
    1: Availability.AVAILABLE,
    2: Availability.ON_ORDER,
}


@dataclass(frozen=True, slots=True)
class ProposalCard:
    seller_key: str
    supplier: Supplier
    offer: Offer


@dataclass(frozen=True, slots=True)
class ProfileCard:
    seller_key: str
    supplier: Supplier


def merge_suppliers(profile: Supplier, proposal: Supplier, source_id: UUID, key: str) -> Supplier:
    """Карточка профиля главнее: данные со страниц товаров лишь дополняют пустое."""
    inn = profile.inn or proposal.inn
    return Supplier(
        supplier_id=identity.supplier_id(inn, source_id, f"profile-{key}"),
        name=profile.name or proposal.name,
        inn=inn,
        kpps=profile.kpps or proposal.kpps,
        region=profile.region or proposal.region,
        website=profile.website or proposal.website,
        contacts={**proposal.contacts, **profile.contacts},
        okved_codes=profile.okved_codes or proposal.okved_codes,
        identity_status=profile.identity_status,
        identity_evidence_url=profile.identity_evidence_url,
    )


def profile_url(user_id: int | str) -> str:
    return f"{BASE_URL}/profile-{user_id}/"


def parse_proposal(html: str, url: str, source_id: UUID, now: datetime) -> ProposalCard:
    state = _state(html, url)
    try:
        proposal = state["proposal"]["proposal"]["data"]
        seller = state["proposal"]["supplier"]["data"]
        proposal_id = str(proposal["id"])
        title = " ".join(str(proposal["title"]).split())
        seller_id = str(seller["id"])
    except (KeyError, TypeError) as error:
        raise ContentFormatError(f"{url}: в состоянии страницы нет товара или продавца") from error
    if not title:
        raise ContentFormatError(f"{url}: у товара нет названия")
    supplier = _supplier(seller, seller_id, source_id)
    offer = _offer(proposal, proposal_id, title, url, supplier, source_id, now)
    return ProposalCard(seller_id, supplier, offer)


def parse_profile(html: str, url: str, source_id: UUID) -> ProfileCard:
    state = _state(html, url)
    try:
        profile = state["profile"]["data"]
        seller_id = str(profile["id"])
        about = (state.get("about") or {}).get("data") or {}
        requisites = (state.get("requisites") or {}).get("data") or {}
        title = _text(profile["title"])
    except (KeyError, TypeError) as error:
        raise ContentFormatError(f"{url}: в состоянии страницы нет профиля") from error
    if not title:
        raise ContentFormatError(f"{url}: у профиля нет названия")
    company = profile.get("company") or {}
    origin = profile.get("origin") or {}
    inn = normalize_inn(_text(requisites.get("inn")))
    kpp = normalize_kpp(_text(requisites.get("kpp")))
    contacts = {
        key: value
        for key, value in (
            ("phone", _text(profile.get("phone"))),
            ("email", _text(profile.get("email"))),
            ("address", _text(profile.get("address"))),
            ("legal_address", _text(requisites.get("legalAddress"))),
            ("ogrn", _text(requisites.get("ogrn"))),
            ("locality", _text(origin.get("title"))),
            ("summary", _text(company.get("summary")) or _text(about.get("description"))),
        )
        if value
    }
    supplier = Supplier(
        supplier_id=identity.supplier_id(inn, source_id, f"profile-{seller_id}"),
        name=title,
        inn=inn,
        kpps=(kpp,) if kpp else (),
        region=_text(origin.get("title")),
        website=_text(profile.get("site")),
        contacts=contacts,
        identity_status=VerificationStatus.UNVERIFIED,
        identity_evidence_url=profile_url(seller_id),
    )
    return ProfileCard(seller_id, supplier)


def _state(html: str, url: str) -> dict[str, Any]:
    match = _STATE.search(html)
    if match is None:
        raise ContentFormatError(f"{url}: на странице нет состояния preloadedState")
    try:
        state = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise ContentFormatError(f"{url}: состояние страницы не разобрано: {error}") from error
    if not isinstance(state, dict):
        raise ContentFormatError(f"{url}: состояние страницы не является объектом")
    return state


def _supplier(seller: dict[str, Any], seller_id: str, source_id: UUID) -> Supplier:
    inn = normalize_inn(_text(seller.get("inn")))
    origin = seller.get("origin") or {}
    city = _text(origin.get("title"))
    contacts = {
        key: value
        for key, value in (
            ("phone", _text(seller.get("phone"))),
            ("address", _text(seller.get("address"))),
            ("locality", city),
            ("summary", _text(seller.get("description"))),
        )
        if value
    }
    url = profile_url(seller_id)
    return Supplier(
        supplier_id=identity.supplier_id(inn, source_id, f"profile-{seller_id}"),
        name=_text(seller.get("name")) or f"Supl.biz {seller_id}",
        inn=inn,
        region=city,
        contacts=contacts,
        identity_status=VerificationStatus.UNVERIFIED,
        identity_evidence_url=url,
    )


def _offer(
    proposal: dict[str, Any],
    proposal_id: str,
    title: str,
    url: str,
    supplier: Supplier,
    source_id: UUID,
    now: datetime,
) -> Offer:
    description = _text(proposal.get("description"))
    categories = _primary_category(proposal)
    attributes = {
        key: value
        for key, value in (
            ("price_details", _text(proposal.get("priceDetails"))),
            ("categories", _other_categories(proposal, categories)),
            ("specification", _specification(proposal.get("specification"))),
        )
        if value
    }
    return Offer(
        offer_id=identity.offer_id(source_id, proposal_id),
        source_id=source_id,
        external_id=proposal_id,
        url=url,
        name=title,
        first_seen_at=now,
        last_seen_at=now,
        supplier_id=supplier.supplier_id,
        seller_status=VerificationStatus.UNVERIFIED,
        evidence_url=supplier.identity_evidence_url,
        description=description,
        item_type=ItemType.UNKNOWN,
        attributes=attributes,
        source_category=categories,
        price=_price(proposal.get("price")),
        currency=_text(proposal.get("currency")),
        availability=_AVAILABILITY.get(
            _integer(proposal.get("availability")), Availability.UNKNOWN
        ),
        content_hash=identity.offer_content_hash(
            name=title,
            description=description,
            item_type=str(ItemType.UNKNOWN),
            attributes=attributes,
        ),
    )


def _category_names(proposal: dict[str, Any], key: str) -> list[str]:
    names: list[str] = []
    for item in proposal.get(key) or []:
        name = _text(item.get("name")) if isinstance(item, dict) else ""
        if name and name not in names:
            names.append(name)
    return names


def _primary_category(proposal: dict[str, Any]) -> str:
    """Путь категории товара: цепочка `breadcrumbs`, а без неё — первая категория.

    Продавцы нередко отмечают десяток несвязанных категорий: склеивать их в одну
    цепочку нельзя, остальные категории сохраняются отдельным атрибутом.
    """
    path = _category_names(proposal, "breadcrumbs")
    if not path:
        path = _category_names(proposal, "categories")[:1]
    return " / ".join(path)


def _other_categories(proposal: dict[str, Any], primary: str) -> str:
    listed = [
        name for name in _category_names(proposal, "categories") if name not in primary.split(" / ")
    ]
    return " | ".join(listed[:MAX_OTHER_CATEGORIES])


def _specification(value: Any) -> str:
    if isinstance(value, dict):
        return _text(value.get("specificationsWithoutSplit"))
    return ""


def _price(value: Any) -> Decimal | None:
    """Неизвестная цена остаётся None: нулевая цена означает «не указана»."""
    if value in (None, ""):
        return None
    try:
        price = Decimal(str(value))
    except InvalidOperation:
        return None
    return price if price > 0 else None


def _integer(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def _text(value: Any) -> str:
    return " ".join(str(value).split()) if value not in (None, "") else ""
