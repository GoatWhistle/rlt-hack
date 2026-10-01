from collections.abc import Collection, Sequence
from datetime import datetime

from src.models.enums import CompanyRole, SupplierRole
from src.models.evidence import Evidence
from src.models.offer_evidence import OfferEvidence

CONTRIBUTORS: dict[CompanyRole, frozenset[SupplierRole]] = {
    CompanyRole.MANUFACTURER: frozenset({SupplierRole.MANUFACTURER}),
    CompanyRole.SUPPLIER_DISTRIBUTOR: frozenset({SupplierRole.DISTRIBUTOR, SupplierRole.RESELLER}),
    CompanyRole.DISTRIBUTOR: frozenset({SupplierRole.DISTRIBUTOR}),
    CompanyRole.SUPPLIER: frozenset({SupplierRole.RESELLER}),
    CompanyRole.SERVICE_PROVIDER: frozenset({SupplierRole.SERVICE_PROVIDER}),
}


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


def _strength(card: OfferEvidence) -> tuple[bool, datetime, str]:
    return (card.seller_confirmed, card.offer.last_seen_at, str(card.offer.offer_id))


class RoleResolver:
    def resolve(self, offers: Sequence[OfferEvidence]) -> tuple[CompanyRole, Evidence | None]:
        current = [
            card
            for card in offers
            if card.is_current and card.offer.supplier_role != SupplierRole.UNKNOWN
        ]
        role = company_role({card.offer.supplier_role for card in current})
        if role == CompanyRole.UNKNOWN:
            return role, None
        backing = [
            card
            for card in current
            if card.offer.supplier_role in CONTRIBUTORS[role] and card.role_evidence is not None
        ]
        if not backing:
            return role, None
        return role, max(backing, key=_strength).role_evidence
