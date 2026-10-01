"""Карточки компаний и товаров ProductCenter."""

import re
from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID

from src.adapter.supplier import identity, jsonld, page
from src.adapter.supplier.errors import ContentFormatError
from src.adapter.supplier.inn import find_inn, find_kpp, normalize_inn
from src.models.enums import Availability, ItemType, SupplierRole, VerificationStatus
from src.models.offer import Offer
from src.models.supplier import Supplier

_PRODUCER = re.compile(r"^/producers/(\d+)/[^/]+/?$")
_FEATURE_LABELS = ("характеристики", "условия продажи", "минимальный заказ")


def supplier_card(content: str, url: str, source_id: UUID) -> Supplier:
    tree = page.parse(content, url)
    organization = jsonld.first_of_types(jsonld.nodes(tree), jsonld.ORGANIZATION_TYPES)
    name = jsonld.text(organization.get("name"))
    if not name:
        raise ContentFormatError(f"{url}: нет карточки производителя с названием Organization")
    address = jsonld.first(organization.get("address"))
    document = page.document_text(tree)
    inn = normalize_inn(jsonld.text(organization.get("taxID"))) or find_inn(document)
    kpp = find_kpp(document)
    producer_id = _PRODUCER.fullmatch(urlsplit(url).path)
    if not producer_id:
        raise ContentFormatError(f"{url}: неверный адрес компании")
    contacts = {
        key: value
        for key, value in (
            ("email", jsonld.text(organization.get("email"))),
            ("phone", jsonld.text(organization.get("telephone"))),
            ("address", jsonld.text(address.get("streetAddress"))),
            ("locality", jsonld.text(address.get("addressLocality"))),
        )
        if value
    }
    if not contacts.get("email"):
        email = tree.cssselect(".contact_information a[href^='mailto:']")
        if email:
            contacts["email"] = email[0].get("href").removeprefix("mailto:")
    if not contacts.get("phone"):
        phone = tree.cssselect(".contact_information a[href^='tel:']")
        if phone:
            contacts["phone"] = " ".join(phone[0].text_content().split())
    website = jsonld.text(organization.get("url"))
    if not page.is_company_site(website, "https://productcenter.ru"):
        website = page.external_link(
            tree, ".contact_information a[href^='http']", "https://productcenter.ru"
        )
    return Supplier(
        supplier_id=identity.supplier_id(inn, source_id, producer_id.group(1)),
        name=name,
        inn=inn,
        kpps=(kpp,) if kpp else (),
        region=jsonld.text(address.get("addressRegion")) or contacts.get("locality", ""),
        website=website,
        contacts=contacts,
        identity_status=VerificationStatus.UNVERIFIED,
        identity_evidence_url=url,
    )


def product_card(content: str, url: str, source_id: UUID, now: datetime) -> Offer:
    tree = page.parse(content, url)
    product = jsonld.first_of_types(jsonld.nodes(tree), jsonld.PRODUCT_TYPES)
    name = jsonld.text(product.get("name")) or page.first_text(tree, "h1")
    if not name:
        raise ContentFormatError(f"{url}: нет названия товара")
    owner = tree.cssselect(".contact_firm_id a[href*='/producers/']")
    owner_url = next(
        (a.get("href") for a in owner if _PRODUCER.fullmatch(urlsplit(a.get("href")).path)),
        "",
    )
    if not owner_url:
        raise ContentFormatError(f"{url}: нет явной ссылки на производителя")
    match = _PRODUCER.fullmatch(urlsplit(owner_url).path)
    if match is None:
        raise ContentFormatError(f"{url}: неверная ссылка на производителя")
    document = page.document_text(tree)
    inn = find_inn(document)
    owner_id = identity.supplier_id(inn, source_id, match.group(1))
    offer_data = jsonld.first(product.get("offers"))
    brand = jsonld.text(jsonld.first(product.get("brand")).get("name"))
    description = jsonld.text(product.get("description")) or page.first_text(
        tree, ".tc_description .iv_text"
    )
    category_nodes = tree.cssselect("li.crumb > div > a[href*='/products/catalog-']")
    category = " ".join(category_nodes[-1].text_content().split()) if category_nodes else ""
    attributes: dict[str, str] = {}
    for index, row in enumerate(tree.cssselect(".iv_features tr"), start=1):
        cells = [" ".join(cell.text_content().split()) for cell in row.cssselect("td, th")]
        if len(cells) != 2 or not all(cells):
            continue
        if cells[0].isdecimal():
            attributes[f"Характеристика {index}"] = " ".join(cells)
        elif cells[0].casefold() not in _FEATURE_LABELS:
            attributes[cells[0]] = cells[1]
    price = jsonld.number(offer_data.get("price"))
    specification = jsonld.first(offer_data.get("priceSpecification"))
    unit = jsonld.text(specification.get("unitText")) or jsonld.text(specification.get("unitCode"))
    article = jsonld.text(product.get("sku")) or jsonld.text(product.get("mpn"))
    availability_url = jsonld.text(offer_data.get("availability"))
    availability = {
        "InStock": Availability.AVAILABLE,
        "OutOfStock": Availability.UNAVAILABLE,
        "PreOrder": Availability.ON_ORDER,
    }.get(availability_url.rsplit("/", 1)[-1], Availability.UNKNOWN)
    product_id = re.fullmatch(r"/products/(\d+)/[^/]+/?", urlsplit(url).path)
    if product_id is None:
        raise ContentFormatError(f"{url}: неверный адрес товара")
    external_id = product_id.group(1)
    return Offer(
        offer_id=identity.offer_id(source_id, external_id),
        source_id=source_id,
        external_id=external_id,
        url=url,
        name=name,
        first_seen_at=now,
        last_seen_at=now,
        supplier_id=owner_id,
        seller_status=VerificationStatus.VERIFIED,
        seller_evidence_url=owner_url,
        description=description,
        item_type=ItemType.GOODS,
        brand=brand,
        article=article,
        attributes=attributes,
        source_category=category,
        price=price,
        currency=jsonld.text(offer_data.get("priceCurrency")) if price is not None else "",
        unit=unit,
        availability=availability,
        supplier_role=SupplierRole.MANUFACTURER,
        role_evidence_url=owner_url,
        role_evidence_text="Карточка производителя ProductCenter",
        content_hash=identity.offer_content_hash(
            name, description, ItemType.GOODS, brand, article, unit, attributes=attributes
        ),
    )
