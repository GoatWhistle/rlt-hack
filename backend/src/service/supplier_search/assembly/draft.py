from dataclasses import dataclass, field
from uuid import UUID

from src.models.candidate import Highlight, ProductMatch
from src.models.enums import CompanyRole
from src.models.evidence import Evidence
from src.models.offer_evidence import OfferEvidence
from src.models.purchase import PurchaseSummary
from src.models.role_context import RoleContext
from src.models.scoring import ChannelRank, Score
from src.models.supplier import Supplier


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
    role_context: RoleContext = field(default_factory=RoleContext)

    def __post_init__(self) -> None:
        if self.total_items < 1:
            raise ValueError("a draft needs at least one requested item")

    @property
    def supplier_id(self) -> UUID:
        return self.supplier.supplier_id

    @property
    def coverage(self) -> float:
        covering = [match for match in self.matches if not match.conflicting]
        return len(covering) / self.total_items

    @property
    def conflicting(self) -> bool:
        return any(match.conflicting for match in self.matches)
