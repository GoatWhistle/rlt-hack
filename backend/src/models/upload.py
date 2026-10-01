from dataclasses import dataclass, field

from src.models.supplier_search import SupplierCandidate


@dataclass(frozen=True)
class Notice:
    lot_id: str
    title: str
    subject: str = ""


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
