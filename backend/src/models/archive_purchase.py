from dataclasses import dataclass
from datetime import date

from src.models.enums import PurchaseOutcome
from src.models.errors import InvalidPurchaseSummaryError


@dataclass(frozen=True, slots=True)
class ArchivePurchase:
    supplier_inn: str
    lot_id: str
    title: str
    published: date
    outcome: PurchaseOutcome
    category: str = ""
    customer_inn: str = ""
    source_system: str = ""
    products: tuple[str, ...] = ()
    snapshot: str = ""

    def __post_init__(self) -> None:
        if not self.lot_id or not self.supplier_inn:
            raise InvalidPurchaseSummaryError("archive purchase needs a lot and a supplier")
