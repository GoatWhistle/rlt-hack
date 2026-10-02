from dataclasses import dataclass, field
from decimal import Decimal

from src.models.search.supplier_search import SupplierCandidate


@dataclass(frozen=True)
class Notice:
    lot_id: str
    title: str
    subject: str = ""
    customer_inn: str = ""
    start_price: Decimal | None = None
    delivery_region: str = ""


@dataclass(frozen=True)
class LotRecommendation:
    notice: Notice
    candidates: list[SupplierCandidate] = field(default_factory=list)


@dataclass(frozen=True)
class Upload:
    upload_id: str
    owner: str
    filename: str
    created_at: str
    lots: list[LotRecommendation]
    ranking_version: str = ""
