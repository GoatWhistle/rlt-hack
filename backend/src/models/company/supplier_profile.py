from dataclasses import dataclass

from src.models.catalog.supplier import Supplier
from src.models.company.evidence import Evidence
from src.models.company.offer_evidence import OfferEvidence
from src.models.enums import CompanyRole


@dataclass(frozen=True, slots=True)
class SupplierProfile:
    supplier: Supplier
    role: CompanyRole
    offers: tuple[OfferEvidence, ...]
    role_evidence: Evidence | None = None
