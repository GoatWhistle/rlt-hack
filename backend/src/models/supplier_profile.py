from dataclasses import dataclass

from src.models.enums import CompanyRole
from src.models.evidence import Evidence
from src.models.offer_evidence import OfferEvidence
from src.models.supplier import Supplier


@dataclass(frozen=True, slots=True)
class SupplierProfile:
    supplier: Supplier
    role: CompanyRole
    offers: tuple[OfferEvidence, ...]
    role_evidence: Evidence | None = None
