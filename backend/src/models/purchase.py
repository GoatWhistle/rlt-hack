from dataclasses import dataclass
from typing import Self

from src.models.enums import PurchaseOutcome
from src.models.errors import InvalidPurchaseSummaryError


@dataclass(frozen=True, slots=True)
class PurchaseRecord:
    lot_id: str
    title: str
    outcome: PurchaseOutcome
    item_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PurchaseSummary:
    similar: int = 0
    wins: int = 0
    records: tuple[PurchaseRecord, ...] = ()

    def __post_init__(self) -> None:
        if self.similar < 0 or self.wins < 0:
            raise InvalidPurchaseSummaryError("counters cannot be negative")
        if self.wins > self.similar:
            raise InvalidPurchaseSummaryError("wins exceed similar purchases")
        if len(self.records) > self.similar:
            raise InvalidPurchaseSummaryError("more records than similar purchases")

    @classmethod
    def empty(cls) -> Self:
        return cls()

    @property
    def item_ids(self) -> frozenset[str]:
        return frozenset(item_id for record in self.records for item_id in record.item_ids)
