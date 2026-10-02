import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

from src.models.enums import IssueCode
from src.models.inn import is_valid_inn
from src.models.procurement import LOT_ID_MAX_LENGTH, LOT_ID_PATTERN, ProcurementLot, RowIssue

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
SPACES = re.compile(r"[\s ]")

type Cells = Callable[[str], str]


def parse_price(raw: str) -> Decimal | None:
    compact = SPACES.sub("", raw).replace(",", ".", 1)
    try:
        value = Decimal(compact)
    except InvalidOperation as error:
        raise ValueError(raw) from error
    if not value.is_finite() or value < 0:
        raise ValueError(raw)
    return value


def parse_date(raw: str) -> date:
    if not ISO_DATE.match(raw):
        raise ValueError(raw)
    return date.fromisoformat(raw[:10])


def _lot_id_issue(row: int, lot_id: str, seen: set[str]) -> RowIssue | None:
    if not lot_id:
        return RowIssue(row, IssueCode.MISSING_LOT_ID)
    if len(lot_id) > LOT_ID_MAX_LENGTH or not LOT_ID_PATTERN.fullmatch(lot_id):
        return RowIssue(row, IssueCode.BAD_LOT_ID, lot_id)
    if lot_id in seen:
        return RowIssue(row, IssueCode.DUPLICATE_LOT, lot_id)
    return None


def _price(row: int, raw: str, issues: list[RowIssue]) -> Decimal | None:
    if not raw:
        return None
    try:
        return parse_price(raw)
    except ValueError:
        issues.append(RowIssue(row, IssueCode.BAD_PRICE, raw))
        return None


def _date(row: int, raw: str, issues: list[RowIssue]) -> date | None:
    if not raw:
        return None
    try:
        return parse_date(raw)
    except ValueError:
        issues.append(RowIssue(row, IssueCode.BAD_DATE, raw))
        return None


def read_lot(row: int, cell: Cells, seen: set[str]) -> ProcurementLot | list[RowIssue]:
    lot_id = cell("lot_id")
    issues: list[RowIssue] = []
    lot_issue = _lot_id_issue(row, lot_id, seen)
    if lot_issue is not None:
        issues.append(lot_issue)
    subject = cell("subject")
    title = cell("procedure_name") or subject
    if not title:
        issues.append(RowIssue(row, IssueCode.MISSING_TITLE))
    price = _price(row, cell("start_price"), issues)
    published = _date(row, cell("publish_date"), issues)
    customer_inn = cell("customer_inn")
    if customer_inn and not is_valid_inn(customer_inn):
        issues.append(RowIssue(row, IssueCode.BAD_INN, customer_inn))
    if issues:
        return issues
    seen.add(lot_id)
    return ProcurementLot(
        lot_id=lot_id,
        title=title,
        row=row,
        subject=subject,
        customer_inn=customer_inn,
        publish_date=published,
        start_price=price,
    )
