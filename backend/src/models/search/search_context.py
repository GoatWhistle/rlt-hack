from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SearchContext:
    customer_inn: str = ""
    start_price: Decimal | None = None
    delivery_region: str = ""
