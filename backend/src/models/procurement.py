import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.models.enums import IssueCode
from src.models.errors import InvalidProcurementLotError, InvalidUploadError
from src.models.search import SearchContext, SearchText

LOT_ID_PATTERN = re.compile(r"[0-9A-Za-z_-]+")
LOT_ID_MAX_LENGTH = 64


def _collapse(value: str) -> str:
    return " ".join(value.split())


@dataclass(frozen=True, slots=True)
class RowIssue:
    row: int
    code: IssueCode
    value: str = ""

    def __post_init__(self) -> None:
        if self.row < 1:
            raise InvalidUploadError("issue rows start at 1")


@dataclass(frozen=True, slots=True)
class ProcurementLot:
    lot_id: str
    title: str
    row: int
    subject: str = ""
    customer_inn: str = ""
    publish_date: date | None = None
    start_price: Decimal | None = None

    def __post_init__(self) -> None:
        if len(self.lot_id) > LOT_ID_MAX_LENGTH or not LOT_ID_PATTERN.fullmatch(self.lot_id):
            raise InvalidProcurementLotError("lot id has a wrong format")
        title = _collapse(self.title)
        if not title:
            raise InvalidProcurementLotError("title is empty")
        if self.row < 1:
            raise InvalidProcurementLotError("rows start at 1")
        price = self.start_price
        if price is not None and (not price.is_finite() or price < 0):
            raise InvalidProcurementLotError("start price must be a non-negative number")
        subject = _collapse(self.subject)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "subject", "" if subject == title else subject)
        object.__setattr__(self, "customer_inn", self.customer_inn.strip())

    @property
    def search_text(self) -> str:
        return (self.subject or self.title)[: SearchText.MAX_LENGTH]

    @property
    def context(self) -> SearchContext:
        return SearchContext(customer_inn=self.customer_inn, start_price=self.start_price)


@dataclass(frozen=True, slots=True)
class NoticeFile:
    lots: tuple[ProcurementLot, ...]
    issues: tuple[RowIssue, ...] = ()

    def __post_init__(self) -> None:
        identifiers = [lot.lot_id for lot in self.lots]
        if len(set(identifiers)) != len(identifiers):
            raise InvalidUploadError("lot ids repeat")

    @property
    def rejected(self) -> int:
        return len({issue.row for issue in self.issues})
