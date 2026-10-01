"""Карточка контракта ЕИС: поставщик, позиции, цена и исполнение.

Разметка сверена по архивным снимкам страниц `common-info`,
`payment-info-and-target-of-order` и `process-info` (web.archive.org, 2021–2022).
Таблицы читаются по заголовкам столбцов с учётом `colspan`. Если таблицы
поставщика нет, разбор завершается ошибкой, а значения не додумываются.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from src.adapter.supplier import page
from src.adapter.supplier.eis_registry.dto import (
    EisContract,
    EisContractItem,
    EisParty,
    ListingEntry,
)
from src.adapter.supplier.errors import ContentFormatError
from src.adapter.supplier.inn import find_inn, find_kpp

_MONEY = re.compile(r"-?\d[\d\s\xa0]*(?:[.,]\d+)?")
_OKPD = re.compile(r"\d{2}\.\d{2}(?:\.\d+)*")
_QUANTITY = re.compile(r"^\s*(-?\d[\d\s\xa0]*(?:[.,]\d+)?)\s*(.*)$")

Table = tuple[list[str], list[list[str]], list[Any]]


def _text(element: Any) -> str:
    return " ".join(element.text_content().split())


def parse_money(raw: str) -> Decimal | None:
    match = _MONEY.search(raw)
    if match is None:
        return None
    cleaned = re.sub(r"[\s\xa0]", "", match.group()).replace(",", ".")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return value if value.is_finite() and value >= 0 else None


def _fields(tree: Any) -> dict[str, str]:
    found: dict[str, str] = {}
    pairs = (
        (".cardMainInfo__title", "cardMainInfo__content"),
        (".section__title", "section__info"),
    )
    for title_css, value_class in pairs:
        for title in tree.cssselect(title_css):
            sibling = title.getnext()
            if sibling is None or value_class not in (sibling.get("class") or ""):
                continue
            found.setdefault(_text(title), _text(sibling))
    return found


def _headers(table: Any) -> list[str]:
    cells = table.xpath("./thead/tr/th") or table.xpath("./tr[1]/th")
    headers: list[str] = []
    for cell in cells:
        span = int(cell.get("colspan") or 1) if (cell.get("colspan") or "1").isdigit() else 1
        headers.extend([_text(cell).casefold()] * span)
    return headers


def _tables(tree: Any) -> list[Table]:
    result: list[Table] = []
    for table in tree.cssselect("table"):
        headers = _headers(table)
        if not headers:
            continue
        rows: list[list[str]] = []
        elements: list[Any] = []
        for row in table.xpath("./tbody/tr | ./tr"):
            cells = row.xpath("./td")
            if len(cells) >= 2 and "hidden" not in (row.get("class") or "").split():
                rows.append([_text(cell) for cell in cells])
                elements.append(cells)
        result.append((headers, rows, elements))
    return result


def _column(headers: list[str], *needles: str) -> int | None:
    for index, header in enumerate(headers):
        if any(needle in header for needle in needles):
            return index
    return None


def _cell(row: list[str], index: int | None) -> str:
    return row[index] if index is not None and index < len(row) else ""


def _organization_name(cell: Any) -> str:
    for section in cell.cssselect("section"):
        section.getparent().remove(section)
    return _text(cell)


def _parties(headers: list[str], rows: list[list[str]], cells: list[Any]) -> list[EisParty]:
    address_col = _column(headers, "адрес")
    parties = []
    for row, row_cells in zip(rows, cells, strict=True):
        full_text = row[0]
        name = _organization_name(row_cells[0])
        if not name:
            continue
        parties.append(
            EisParty(
                name=name,
                inn=find_inn(full_text),
                kpp=find_kpp(full_text),
                address=_cell(row, address_col),
            )
        )
    return parties


def _quantity(raw: str) -> tuple[Decimal | None, str]:
    match = _QUANTITY.match(raw)
    if match is None:
        return None, raw.strip()
    return parse_money(match.group(1)), match.group(2).strip()


def _items(headers: list[str], rows: list[list[str]]) -> list[EisContractItem]:
    name_col = _column(headers, "наименование")
    okpd_col = _column(headers, "окпд", "ктру")
    quantity_col = _column(headers, "количество")
    price_col = _column(headers, "цена за")
    total_col = _column(headers, "сумма")
    items = []
    for row in rows:
        name = _cell(row, name_col)
        if not name or len(row) < len(headers):
            continue
        quantity, unit = _quantity(_cell(row, quantity_col))
        okpd = _OKPD.search(_cell(row, okpd_col))
        items.append(
            EisContractItem(
                name=name,
                okpd2_code=okpd.group() if okpd else "",
                unit=unit,
                quantity=quantity,
                unit_price=parse_money(_cell(row, price_col)),
                total_price=parse_money(_cell(row, total_col)),
            )
        )
    return items


def _by_label(fields: dict[str, str], *needles: str) -> str:
    for label, value in fields.items():
        lowered = label.casefold()
        if all(needle in lowered for needle in needles):
            return value
    return ""


def parse_card(text: str, entry: ListingEntry) -> EisContract:
    tree = page.parse(text, entry.card_url)
    fields = _fields(tree)
    suppliers: list[EisParty] = []
    for headers, rows, cells in _tables(tree):
        if _column(headers, "организация") is not None and not suppliers:
            suppliers = _parties(headers, rows, cells)
    if not suppliers:
        raise ContentFormatError(f"В карточке контракта нет таблицы поставщика: {entry.card_url}")
    states = tree.cssselect(".cardMainInfo__state")
    return EisContract(
        reestr_number=entry.reestr_number,
        url=entry.card_url,
        law=entry.law,
        customer=entry.customer or _by_label(fields, "заказчик"),
        status=(_text(states[0]) if states else "") or _by_label(fields, "статус"),
        signed_on=_by_label(fields, "дата заключения"),
        execution_end=_by_label(fields, "окончания исполнения"),
        price=parse_money(_by_label(fields, "цена контракта")),
        suppliers=tuple(suppliers),
        fields=fields,
    )


def parse_items(text: str, url: str) -> tuple[EisContractItem, ...]:
    tree = page.parse(text, url)
    for headers, rows, _ in _tables(tree):
        if _column(headers, "наименование объекта") is not None and (
            _column(headers, "количество") is not None
        ):
            return tuple(_items(headers, rows))
    raise ContentFormatError(f"На странице нет таблицы объектов закупки: {url}")


def parse_execution(text: str, url: str) -> tuple[Decimal | None, Decimal | None]:
    """Стоимость исполненных обязательств и оплаченное по этапам контракта."""
    tree = page.parse(text, url)
    executed: Decimal | None = None
    paid: Decimal | None = None
    for headers, rows, _ in _tables(tree):
        stage_col = _column(headers, "этап контракта")
        executed_col = _column(headers, "исполненных обязательств")
        paid_col = _column(headers, "фактически оплачено")
        if stage_col is None or executed_col is None or paid_col is None:
            continue
        for row in rows:
            if len(row) != len(headers):
                continue
            value = parse_money(_cell(row, executed_col))
            if value is not None:
                executed = (executed or Decimal(0)) + value
            value = parse_money(_cell(row, paid_col))
            if value is not None:
                paid = (paid or Decimal(0)) + value
    return executed, paid
