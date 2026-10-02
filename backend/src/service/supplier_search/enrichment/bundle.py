from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import UUID

from src.models.catalog.supplier import Supplier
from src.models.company.offer_evidence import OfferEvidence
from src.models.company.purchase import PurchaseSummary


@dataclass(frozen=True, slots=True)
class Enrichment:
    suppliers: Mapping[UUID, Supplier] = field(default_factory=dict)
    offers: Mapping[UUID, OfferEvidence] = field(default_factory=dict)
    current: Mapping[UUID, tuple[OfferEvidence, ...]] = field(default_factory=dict)
    histories: Mapping[UUID, PurchaseSummary] = field(default_factory=dict)
    failed: frozenset[str] = frozenset()

    @property
    def degraded(self) -> bool:
        return bool(self.failed)

    def history_of(self, supplier_id: UUID) -> PurchaseSummary:
        return self.histories.get(supplier_id, PurchaseSummary.empty())

    def current_of(self, supplier_id: UUID) -> tuple[OfferEvidence, ...]:
        return self.current.get(supplier_id, ())
