from dataclasses import dataclass, field
from decimal import Decimal

from src.models.search.supplier_search import SupplierCandidate


@dataclass(frozen=True)
class NoticePosition:
    item_id: str
    name: str
    okpd2: str = ""


@dataclass(frozen=True)
class Notice:
    lot_id: str
    title: str
    subject: str = ""
    customer_inn: str = ""
    start_price: Decimal | None = None
    delivery_region: str = ""
    positions: tuple[NoticePosition, ...] = ()

    @property
    def query_text(self) -> str:
        names = sorted({item.name for item in self.positions})
        codes = " ".join(sorted({item.okpd2 for item in self.positions if item.okpd2}))
        return "\n".join(filter(None, (self.title, self.subject, *names, codes)))


@dataclass(frozen=True)
class LotRecommendation:
    notice: Notice
    candidates: list[SupplierCandidate] = field(default_factory=list)
    processed: bool = True
    failed: bool = False


@dataclass(frozen=True)
class Upload:
    upload_id: str
    owner: str
    filename: str
    created_at: str
    lots: list[LotRecommendation]
    ranking_version: str = ""
