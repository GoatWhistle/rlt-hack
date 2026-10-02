from dataclasses import dataclass, field
from uuid import UUID

from src.models.catalog.supplier import Supplier
from src.models.company.evidence import Evidence
from src.models.company.offer_evidence import OfferEvidence
from src.models.company.purchase import PurchaseSummary
from src.models.enums import CompanyRole
from src.models.ranking.scoring import ChannelRank, Score
from src.models.search.candidate import Highlight, ProductMatch


@dataclass(frozen=True, slots=True)
class CandidateDraft:
    supplier: Supplier
    role: CompanyRole
    fusion: Score
    total_items: int
    role_evidence: Evidence | None = None
    channels: tuple[ChannelRank, ...] = ()
    matches: tuple[ProductMatch, ...] = ()
    used_offers: tuple[OfferEvidence, ...] = ()
    current_offers: tuple[OfferEvidence, ...] = ()
    history: PurchaseSummary = field(default_factory=PurchaseSummary.empty)
    highlights: tuple[Highlight, ...] = ()
    enrichment_failed: bool = False

    def __post_init__(self) -> None:
        if self.total_items < 1:
            raise ValueError("a draft needs at least one requested item")

    @property
    def supplier_id(self) -> UUID:
        return self.supplier.supplier_id

    @property
    def coverage(self) -> float:
        return len(self.matches) / self.total_items
