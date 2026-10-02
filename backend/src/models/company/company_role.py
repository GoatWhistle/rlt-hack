from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime

from src.models.company.evidence import Evidence
from src.models.company.offer_evidence import OfferEvidence
from src.models.enums import CompanyRole, SupplierRole

CONTRIBUTORS: dict[CompanyRole, frozenset[SupplierRole]] = {
    CompanyRole.MANUFACTURER: frozenset({SupplierRole.MANUFACTURER}),
    CompanyRole.SUPPLIER_DISTRIBUTOR: frozenset({SupplierRole.DISTRIBUTOR, SupplierRole.RESELLER}),
    CompanyRole.DISTRIBUTOR: frozenset({SupplierRole.DISTRIBUTOR}),
    CompanyRole.SUPPLIER: frozenset({SupplierRole.RESELLER}),
    CompanyRole.SERVICE_PROVIDER: frozenset({SupplierRole.SERVICE_PROVIDER}),
}


@dataclass(frozen=True, slots=True)
class RoleAssessment:
    role: CompanyRole
    evidence: Evidence | None = None

    @property
    def confirmed(self) -> bool:
        return self.role != CompanyRole.UNKNOWN and self.evidence is not None


def company_role(roles: Collection[SupplierRole]) -> CompanyRole:
    if SupplierRole.MANUFACTURER in roles:
        return CompanyRole.MANUFACTURER
    if SupplierRole.DISTRIBUTOR in roles and SupplierRole.RESELLER in roles:
        return CompanyRole.SUPPLIER_DISTRIBUTOR
    if SupplierRole.DISTRIBUTOR in roles:
        return CompanyRole.DISTRIBUTOR
    if SupplierRole.RESELLER in roles:
        return CompanyRole.SUPPLIER
    if SupplierRole.SERVICE_PROVIDER in roles:
        return CompanyRole.SERVICE_PROVIDER
    return CompanyRole.UNKNOWN


def _freshness(card: OfferEvidence) -> tuple[datetime, str]:
    return (card.offer.last_seen_at, str(card.offer.offer_id))


def _role_of(cards: Sequence[OfferEvidence]) -> CompanyRole:
    return company_role({card.offer.supplier_role for card in cards})


def assess_role(offers: Sequence[OfferEvidence]) -> RoleAssessment:
    current = [
        card
        for card in offers
        if card.is_current and card.offer.supplier_role != SupplierRole.UNKNOWN
    ]
    backed = [card for card in current if card.backs_supplier]
    role = _role_of(backed)
    if role == CompanyRole.UNKNOWN:
        return RoleAssessment(_role_of(current))
    backing = [
        card
        for card in backed
        if card.offer.supplier_role in CONTRIBUTORS[role] and card.role_evidence is not None
    ]
    if not backing:
        return RoleAssessment(role)
    return RoleAssessment(role, max(backing, key=_freshness).role_evidence)
