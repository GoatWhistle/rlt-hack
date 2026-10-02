from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar, Self

from src.models.enums import ItemType, Locale, SearchOrigin
from src.models.errors import (
    EmptySearchTextError,
    InvalidCandidateLimitError,
    InvalidSearchContextError,
    SearchTextTooLongError,
)
from src.models.inn import is_valid_inn


@dataclass(frozen=True, slots=True)
class SearchText:
    value: str

    MAX_LENGTH: ClassVar[int] = 4000

    def __post_init__(self) -> None:
        normalized = " ".join(self.value.split())
        if not normalized:
            raise EmptySearchTextError
        if len(normalized) > self.MAX_LENGTH:
            raise SearchTextTooLongError(self.MAX_LENGTH)
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True, slots=True)
class CandidateLimit:
    value: int

    MIN: ClassVar[int] = 1
    MAX: ClassVar[int] = 50
    DEFAULT: ClassVar[int] = 20

    def __post_init__(self) -> None:
        if not self.MIN <= self.value <= self.MAX:
            raise InvalidCandidateLimitError(self.MIN, self.MAX)

    @classmethod
    def default(cls) -> Self:
        return cls(cls.DEFAULT)


@dataclass(frozen=True, slots=True)
class SearchFilters:
    regions: tuple[str, ...] = ()
    item_type: ItemType | None = None

    def __post_init__(self) -> None:
        cleaned = tuple(dict.fromkeys(region.strip() for region in self.regions if region.strip()))
        object.__setattr__(self, "regions", cleaned)

    @property
    def is_empty(self) -> bool:
        return not self.regions and self.item_type is None


@dataclass(frozen=True, slots=True)
class SearchContext:
    customer_inn: str = ""
    start_price: Decimal | None = None

    def __post_init__(self) -> None:
        inn = self.customer_inn.strip()
        if inn and not is_valid_inn(inn):
            raise InvalidSearchContextError("customer inn fails the checksum")
        price = self.start_price
        if price is not None and (not price.is_finite() or price < 0):
            raise InvalidSearchContextError("start price must be a non-negative number")
        object.__setattr__(self, "customer_inn", inn)

    @property
    def fields(self) -> tuple[str, ...]:
        present = (
            ("customerInn", bool(self.customer_inn)),
            ("startPrice", self.start_price is not None),
        )
        return tuple(name for name, given in present if given)

    @property
    def is_empty(self) -> bool:
        return not self.fields


@dataclass(frozen=True, slots=True)
class SearchQuery:
    text: SearchText
    limit: CandidateLimit = field(default_factory=CandidateLimit.default)
    locale: Locale = Locale.RU
    filters: SearchFilters = field(default_factory=SearchFilters)
    context: SearchContext = field(default_factory=SearchContext)
    origin: SearchOrigin = SearchOrigin.MANUAL
