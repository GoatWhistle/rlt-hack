"""DTO внешнего формата ЕИС: исторические контракты не являются текущими Offer."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class DateWindow:
    start: date
    end: date

    def days(self) -> int:
        return (self.end - self.start).days + 1

    def split(self) -> tuple["DateWindow", "DateWindow"]:
        middle = self.start.toordinal() + (self.days() - 1) // 2
        left_end = date.fromordinal(middle)
        return (
            DateWindow(self.start, left_end),
            DateWindow(date.fromordinal(middle + 1), self.end),
        )


CENT = Decimal("0.01")
PRICE_CEILING = Decimal("100000000000000")


@dataclass(frozen=True, slots=True)
class PriceRange:
    low: Decimal
    high: Decimal

    def splittable(self) -> bool:
        return self.high - self.low > CENT

    def split(self) -> tuple["PriceRange", "PriceRange"]:
        if self.low > 0 and self.high / self.low > 8:
            middle = (self.low * self.high).sqrt().quantize(CENT)
        else:
            middle = (self.low + (self.high - self.low) / 2).quantize(CENT)
        middle = min(max(middle, self.low), self.high - CENT)
        return PriceRange(self.low, middle), PriceRange(middle + CENT, self.high)


@dataclass(frozen=True, slots=True)
class Slice:
    window: DateWindow
    price: PriceRange | None = None

    def narrow(self) -> tuple["Slice", "Slice"] | None:
        """Делит срез, чья выдача упёрлась в предел сайта; None — делить некуда."""
        if self.window.days() > 1:
            left, right = self.window.split()
            return Slice(left, self.price), Slice(right, self.price)
        price = self.price or PriceRange(CENT, PRICE_CEILING)
        if not price.splittable():
            return None
        low, high = price.split()
        return Slice(self.window, low), Slice(self.window, high)


@dataclass(frozen=True, slots=True)
class ListingEntry:
    reestr_number: str
    card_url: str
    law: str = ""
    customer: str = ""
    status: str = ""


@dataclass(frozen=True, slots=True)
class ListingPage:
    total: int
    entries: tuple[ListingEntry, ...]
    lower_bound: bool = False


@dataclass(frozen=True, slots=True)
class EisParty:
    name: str
    inn: str | None = None
    kpp: str | None = None
    address: str = ""


@dataclass(frozen=True, slots=True)
class EisContractItem:
    name: str
    okpd2_code: str = ""
    unit: str = ""
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    total_price: Decimal | None = None


@dataclass(frozen=True, slots=True)
class EisContract:
    reestr_number: str
    url: str
    law: str = ""
    customer: str = ""
    status: str = ""
    signed_on: str = ""
    execution_end: str = ""
    price: Decimal | None = None
    executed_amount: Decimal | None = None
    paid_amount: Decimal | None = None
    suppliers: tuple[EisParty, ...] = ()
    items: tuple[EisContractItem, ...] = ()
    fields: dict[str, str] = field(default_factory=dict)
