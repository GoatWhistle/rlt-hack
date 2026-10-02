import re
from dataclasses import dataclass
from decimal import Decimal

from src.models.enums import ItemOrigin, ItemType
from src.models.errors import (
    InvalidQuantityError,
    InvalidQueryItemError,
    InvalidSearchRequestError,
)
from src.models.search.search import SearchQuery

OKPD2_PATTERN = re.compile(r"^\d{2}(\.\d{1,3}){0,4}$")


@dataclass(frozen=True, slots=True)
class Quantity:
    value: Decimal
    unit: str

    def __post_init__(self) -> None:
        unit = self.unit.strip()
        if not self.value.is_finite() or self.value <= 0 or not unit:
            raise InvalidQuantityError
        object.__setattr__(self, "unit", unit)


@dataclass(frozen=True, slots=True)
class QueryItem:
    item_id: str
    name: str
    origin: ItemOrigin = ItemOrigin.TEXT
    okpd2: str = ""
    item_type: ItemType = ItemType.UNKNOWN
    quantity: Quantity | None = None

    def __post_init__(self) -> None:
        if not self.item_id.strip():
            raise InvalidQueryItemError("item id is empty")
        name = " ".join(self.name.split())
        if not name:
            raise InvalidQueryItemError("name is empty")
        if self.okpd2 and not OKPD2_PATTERN.fullmatch(self.okpd2):
            raise InvalidQueryItemError("okpd2 code has a wrong format")
        object.__setattr__(self, "name", name)


@dataclass(frozen=True, slots=True)
class SearchRequest:
    query: SearchQuery
    items: tuple[QueryItem, ...]

    def __post_init__(self) -> None:
        if not self.items:
            raise InvalidSearchRequestError("no items")
        identifiers = [item.item_id for item in self.items]
        if len(set(identifiers)) != len(identifiers):
            raise InvalidSearchRequestError("item ids repeat")

    @property
    def item_ids(self) -> tuple[str, ...]:
        return tuple(item.item_id for item in self.items)
