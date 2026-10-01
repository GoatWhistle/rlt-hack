"""Адаптер каталога компаний ОптКаталог (optkatalog.ru).

Адреса карточек берутся из `sitemap.xml`: перебор разделов с сортировкой и
постраничной навигацией закрыт в `robots.txt`, а публичного API у источника нет.
Карточка компании — лист дерева разделов `/postavschiki/`, поэтому от адреса
раздела она отличается наличием потомков в самом sitemap.

Разметки schema.org о компании на карточке нет: реквизиты размечены
заголовками блока описания («Юридическое наименование», «ИНН/ОГРН», «Товары,
услуги», «Адрес», «Контакты»), а свойства — списком `ty-product-feature`.
Строки блока «Товары, услуги» сохраняются предложениями без цены: карточка
публикует номенклатуру, а не прайс.
"""

import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from src.adapter.supplier import identity, page, sitemap
from src.adapter.supplier.errors import SourceUnavailableError
from src.adapter.supplier.inn import find_inn, find_kpp, normalize_inn
from src.models.enums import ItemType, SupplierRole, VerificationStatus
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier

logger = logging.getLogger(__name__)

PROVIDER_NAME = "optkatalog_web"

BASE_URL = "https://optkatalog.ru/"

SITEMAP_URL = "https://optkatalog.ru/sitemap.xml"

# Карточки компаний лежат в дереве разделов базы поставщиков.
CARD_PREFIX = "/postavschiki/"

# Раздел, подраздел и имя компании: более короткий адрес — это раздел каталога.
CARD_MIN_SEGMENTS = 4

# Значение заголовка обязано быть ASCII: контакт указывается при развёртывании.
USER_AGENT = "rlt-supplier-search/0.1 (+contact: see deployment configuration)"

_DESCRIPTION = "#content_description"
_CONTACTS = "#content_description details a[href^='http']"
_FEATURE = ".ty-product-feature"
_FEATURE_LABEL = ".ty-product-feature__label"
_FEATURE_VALUE = ".ty-product-feature__value"

_LEGAL_NAME_LABEL = "юридическое наименование"
_TAX_LABEL = "инн/огрн"
_FOUNDED_LABEL = "год основания"
_ADDRESS_LABEL = "адрес"

# Реквизит бывает и заголовком блока, и строкой «Метка: значение» внутри него.
_INLINE_LABELS = frozenset({_LEGAL_NAME_LABEL, _TAX_LABEL, _FOUNDED_LABEL, _ADDRESS_LABEL})

# Блок ассортимента называется по-разному: «Товары, услуги», «Продукция, услуги».
_PRODUCT_LABELS = ("товар", "продукц", "ассортимент", "услуг")

# Длинная строка блока — рассказ о компании, а не позиция номенклатуры.
MAX_ITEM_WORDS = 14

_CITY_FEATURE = "город"
_COUNTRY_FEATURE = "страна"
_ROLE_FEATURE = "тип компании"
_MIN_ORDER_FEATURE = "минимальный заказ"

# Свойство перечисляет несколько типов сразу («Оптовый поставщик, Производитель»),
# поэтому роли проверяются по порядку: собственное производство важнее перепродажи.
_ROLES = (
    ("производитель", SupplierRole.MANUFACTURER),
    ("завод", SupplierRole.MANUFACTURER),
    ("дистрибьютор", SupplierRole.DISTRIBUTOR),
    ("дилер", SupplierRole.DISTRIBUTOR),
    ("оптов", SupplierRole.RESELLER),
    ("магазин", SupplierRole.RESELLER),
    ("услуг", SupplierRole.SERVICE_PROVIDER),
)

_HEADING_TAGS = frozenset({"h2", "h3", "h4"})

_LINE_BREAK_TAGS = frozenset({"br", "li", "p"})

# Разделитель значений внутри блока: в тексте страницы он не встречается.
_SEPARATOR = "\x00"

_INLINE_FIELD = re.compile(r"^([^:]{2,40}):\s*(.+)$")

# В блоке реквизитов ИНН идёт первым номером, за ним ОГРН.
_TAX_NUMBER = re.compile(r"\d{10,15}")

# Регион читается из адреса: отдельного поля у карточки нет.
_REGION_PART = re.compile(r"\b(обл|край|респ|округ|автономн)", re.IGNORECASE)


class OptKatalogWebProvider:
    """Обходит карточки компаний из sitemap и собирает их реквизиты."""

    def __init__(
        self,
        source_defaults: Source,
        sitemap_url: str = SITEMAP_URL,
        max_companies: int = 500,
        max_concurrent: int = 4,
        http_timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._source = source_defaults
        self._sitemap_url = sitemap_url
        self._max_companies = max_companies
        self._max_concurrent = max(1, max_concurrent)
        self._http_timeout = http_timeout
        self._transport = transport

    @property
    def source(self) -> Source:
        return self._source

    async def fetch(self) -> SupplierPackage:
        headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self._http_timeout),
            headers=headers,
            follow_redirects=True,
            transport=self._transport,
        ) as http:
            company_urls = await self._company_urls(http)
            limit = asyncio.Semaphore(self._max_concurrent)
            cards = await asyncio.gather(
                *(self._card(http, url, limit) for url in company_urls),
                return_exceptions=True,
            )
        suppliers: dict[str, Supplier] = {}
        offers: list[Offer] = []
        for url, card in zip(company_urls, cards, strict=True):
            if isinstance(card, BaseException):
                logger.warning("Карточка компании %s не прочитана: %s", url, card)
                continue
            supplier, products = card
            if supplier is None:
                continue
            suppliers[str(supplier.supplier_id)] = supplier
            offers.extend(products)
        logger.info(
            "ОптКаталог: карточек — %d, компаний — %d, позиций — %d",
            len(company_urls),
            len(suppliers),
            len(offers),
        )
        return SupplierPackage(
            source=self._source,
            suppliers=tuple(suppliers.values()),
            offers=tuple(offers),
        )

    async def _company_urls(self, http: httpx.AsyncClient) -> list[str]:
        urls = await sitemap.read_urls(http, self._sitemap_url)
        cards = _card_urls(urls)
        if not cards:
            raise SourceUnavailableError(f"{self._sitemap_url}: в sitemap нет карточек компаний")
        return cards[: self._max_companies]

    async def _card(
        self,
        http: httpx.AsyncClient,
        url: str,
        limit: asyncio.Semaphore,
    ) -> tuple[Supplier | None, tuple[Offer, ...]]:
        async with limit:
            response = await http.get(url)
            response.raise_for_status()
        tree = await asyncio.to_thread(page.parse, response.text, str(response.url))
        name = page.first_text(tree, "h1")
        blocks = _description_blocks(tree)
        features = _features(tree)
        if not name or not (blocks or features):
            logger.warning("Карточка %s пропущена: на странице нет реквизитов компании", url)
            return None, ()
        supplier = self._supplier(tree, name, blocks, features, url)
        role = _role(features.get(_ROLE_FEATURE, ""))
        products = _products(blocks)
        return supplier, tuple(self._offer(item, url, supplier, role) for item in products)

    def _supplier(
        self,
        tree: Any,
        name: str,
        blocks: dict[str, tuple[str, ...]],
        features: dict[str, str],
        url: str,
    ) -> Supplier:
        address = " ".join(blocks.get(_ADDRESS_LABEL, ()))
        city = features.get(_CITY_FEATURE, "")
        inn = _tax_number(blocks.get(_TAX_LABEL, ())) or find_inn(_description_text(tree))
        kpp = find_kpp(page.document_text(tree))
        contacts = {
            key: value
            for key, value in (
                ("legal_name", _first_line(blocks.get(_LEGAL_NAME_LABEL, ()))),
                ("founded", _first_line(blocks.get(_FOUNDED_LABEL, ()))),
                ("address", address),
                ("country", features.get(_COUNTRY_FEATURE, "")),
                ("company_type", features.get(_ROLE_FEATURE, "")),
                ("min_order", features.get(_MIN_ORDER_FEATURE, "")),
                ("phone", _contact_link(tree, "tel:")),
                ("email", _contact_link(tree, "mailto:")),
            )
            if value
        }
        return Supplier(
            supplier_id=identity.supplier_id(inn, self._source.source_id, url),
            name=name,
            inn=inn,
            kpps=(kpp,) if kpp else (),
            region=_region(address) or city,
            website=_company_site(tree, self._source.base_url),
            contacts=contacts,
            # Каталог не подтверждает реквизиты: статус проверяет отдельная джоба.
            identity_status=VerificationStatus.UNVERIFIED,
            identity_evidence_url=url,
        )

    def _offer(self, name: str, url: str, supplier: Supplier, role: SupplierRole) -> Offer:
        external_id = f"{url}#{name}"
        observed_at = datetime.now(UTC)
        return Offer(
            offer_id=identity.offer_id(self._source.source_id, external_id),
            source_id=self._source.source_id,
            external_id=external_id,
            url=url,
            name=name,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
            supplier_id=supplier.supplier_id,
            seller_status=VerificationStatus.UNVERIFIED,
            seller_evidence_url=url,
            item_type=ItemType.GOODS,
            # Роль объявлена самой компанией в свойстве «Тип компании».
            supplier_role=role,
            role_evidence_url=url,
            role_evidence_text=supplier.contacts.get("company_type", ""),
            content_hash=identity.offer_content_hash(name=name, item_type=str(ItemType.GOODS)),
        )


def _card_urls(urls: list[str]) -> list[str]:
    """Карточка — лист дерева разделов: у адреса раздела есть вложенные адреса."""
    known = {url.rstrip("/") for url in urls}
    found: list[str] = []
    for url in urls:
        path = urlsplit(url).path
        if not path.startswith(CARD_PREFIX):
            continue
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) < CARD_MIN_SEGMENTS:
            continue
        prefix = url.rstrip("/") + "/"
        if any(other.startswith(prefix) for other in known):
            continue
        found.append(url)
    return found


def _description_blocks(tree: Any) -> dict[str, tuple[str, ...]]:
    """Блоки описания: заголовок — метка реквизита, текст до следующего — значение."""
    blocks: dict[str, list[str]] = {}
    for container in tree.cssselect(_DESCRIPTION):
        for heading in container.cssselect("h2, h3, h4"):
            label = " ".join(heading.text_content().split()).casefold().rstrip(":")
            lines = blocks.setdefault(label, [])
            for element in heading.itersiblings():
                if element.tag in _HEADING_TAGS:
                    break
                for line in _lines(element):
                    inline = _INLINE_FIELD.match(line)
                    name = inline.group(1).strip().casefold() if inline else ""
                    if name in _INLINE_LABELS:
                        blocks.setdefault(name, []).append(inline.group(2).strip())
                    else:
                        lines.append(line)
    return {label: tuple(lines) for label, lines in blocks.items() if lines}


def _lines(element: Any) -> list[str]:
    """Строки элемента: значения разделяют только `br` и пункты списка.

    Перенос строки в исходном тексте разделителем не считается: вёрстка
    переносит один абзац произвольно.
    """
    text = ""
    for node in element.iter():
        if node.tag in _LINE_BREAK_TAGS:
            text += _SEPARATOR
        text += node.text or ""
        text += node.tail or ""
    return [" ".join(line.split()) for line in text.split(_SEPARATOR) if len(line.split()) > 0]


def _features(tree: Any) -> dict[str, str]:
    """Свойства карточки: значение может быть списком, он собирается через запятую."""
    found: dict[str, str] = {}
    for element in tree.cssselect(_FEATURE):
        label = page.first_text(element, _FEATURE_LABEL).casefold().rstrip(":")
        values = [line for value in element.cssselect(_FEATURE_VALUE) for line in _lines(value)]
        if label and values:
            found.setdefault(label, ", ".join(values))
    return found


def _role(value: str) -> SupplierRole:
    declared = value.casefold()
    for key, role in _ROLES:
        if key in declared:
            return role
    return SupplierRole.UNKNOWN


def _tax_number(values: tuple[str, ...]) -> str | None:
    """Блок «ИНН/ОГРН» перечисляет номера без подписей: ИНН — первый подходящий."""
    for value in values:
        for match in _TAX_NUMBER.finditer(value):
            inn = normalize_inn(match.group())
            if inn:
                return inn
    return None


def _products(blocks: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    """Строки блока ассортимента: длинные абзацы описывают компанию, а не позиции."""
    for label, lines in blocks.items():
        if label in _INLINE_LABELS or not any(key in label for key in _PRODUCT_LABELS):
            continue
        return tuple(line for line in lines if 0 < len(line.split()) <= MAX_ITEM_WORDS)
    return ()


def _description_text(tree: Any) -> str:
    return " ".join(page.first_text(tree, _DESCRIPTION).split())


def _first_line(lines: tuple[str, ...]) -> str:
    return lines[0] if lines else ""


def _region(address: str) -> str:
    for part in address.split(","):
        if _REGION_PART.search(part):
            return " ".join(part.split())
    return ""


def _company_site(tree: Any, base_url: str) -> str:
    """Сайт компании указан в блоке контактов; остальные ссылки описания — запасной вариант."""
    return page.external_link(tree, _CONTACTS, base_url) or page.external_link(
        tree, f"{_DESCRIPTION} a[href^='http']", base_url
    )


def _contact_link(tree: Any, scheme: str) -> str:
    for href in page.links(tree, f"{_DESCRIPTION} a[href^='{scheme}']"):
        return href.removeprefix(scheme)
    return ""
