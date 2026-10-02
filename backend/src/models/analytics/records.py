"""Записи каталога, объясняющие показатель аналитики."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class RecordProblem(StrEnum):
    STALE = "stale"
    UNKNOWN_AGE = "unknown_age"
    NO_CATEGORY = "no_category"
    NO_PRICE = "no_price"
    NO_SUPPLIER = "no_supplier"
    UNVERIFIED_SELLER = "unverified_seller"
    NO_ATTRIBUTES = "no_attributes"


@dataclass(frozen=True, slots=True)
class RecordQuery:
    category: str | None = None
    problem: RecordProblem | None = None
    limit: int = 25
    offset: int = 0


@dataclass(frozen=True, slots=True)
class RecordRow:
    offer_id: UUID
    name: str
    source_id: UUID
    source_name: str
    supplier_id: UUID | None
    supplier_name: str
    okpd2_code: str
    price: Decimal | None
    currency: str
    url: str
    last_seen_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RecordPage:
    as_of: datetime
    total: int
    items: tuple[RecordRow, ...]
    changed_after: int
