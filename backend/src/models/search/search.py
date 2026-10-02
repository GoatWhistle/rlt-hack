from dataclasses import dataclass, field
from typing import ClassVar, Self

from src.models.enums import ItemType, Locale
from src.models.errors import (
    EmptySearchTextError,
    InvalidCandidateLimitError,
    SearchTextTooLongError,
)


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
class SearchQuery:
    text: SearchText
    limit: CandidateLimit = field(default_factory=CandidateLimit.default)
    locale: Locale = Locale.RU
    filters: SearchFilters = field(default_factory=SearchFilters)
    preferred_region: str = ""
