import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from src.models.enums import CompanyRole, EvidenceKind, RoleBasis, SupplierRole
from src.models.evidence import Evidence
from src.models.offer_evidence import OfferEvidence
from src.models.role_context import RoleContext
from src.models.supplier import Supplier

REGISTRY_SEARCH = "https://rmsp.nalog.ru/search.html?query={inn}"
REGISTRY_DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
OKVED_MARK = "ОКВЭД"

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
    basis: RoleBasis = RoleBasis.NONE
    product: str = ""
    note: str = ""
    conflict: bool = False

    @property
    def confirmed(self) -> bool:
        return self.role != CompanyRole.UNKNOWN and self.evidence is not None

    @property
    def context(self) -> RoleContext:
        return RoleContext(self.basis, self.product, self.note, self.conflict)


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


def _offer_role(offers: Sequence[OfferEvidence]) -> RoleAssessment:
    current = [
        card
        for card in offers
        if card.is_current and card.offer.supplier_role != SupplierRole.UNKNOWN
    ]
    backed = [card for card in current if card.backs_supplier]
    role = _role_of(backed)
    if role == CompanyRole.UNKNOWN:
        fallback = _role_of(current)
        basis = RoleBasis.NONE if fallback == CompanyRole.UNKNOWN else RoleBasis.OFFER
        return RoleAssessment(fallback, basis=basis)
    backing = [
        card
        for card in backed
        if card.offer.supplier_role in CONTRIBUTORS[role] and card.role_evidence is not None
    ]
    if not backing:
        return RoleAssessment(role, basis=RoleBasis.OFFER)
    best = max(backing, key=_freshness)
    return RoleAssessment(role, best.role_evidence, RoleBasis.OFFER, best.offer.name)


def _registry_date(note: str) -> datetime | None:
    found = REGISTRY_DATE.search(note)
    if found is None:
        return None
    day, month, year = (int(part) for part in found.groups())
    try:
        return datetime(year, month, day, tzinfo=UTC)
    except ValueError:
        return None


def registry_role(supplier: Supplier) -> RoleAssessment:
    role = company_role({supplier.role})
    note = supplier.role_evidence
    if role == CompanyRole.UNKNOWN or not note:
        return RoleAssessment(CompanyRole.UNKNOWN)
    if OKVED_MARK in note:
        return RoleAssessment(role, basis=RoleBasis.OKVED, note=note)
    checked = _registry_date(note)
    if checked is None or not supplier.has_valid_inn:
        return RoleAssessment(role, basis=RoleBasis.REGISTRY, note=note)
    evidence = Evidence(
        EvidenceKind.REGISTRY, note, REGISTRY_SEARCH.format(inn=supplier.inn), checked
    )
    return RoleAssessment(role, evidence, RoleBasis.REGISTRY, note=note)


def assess_role(
    offers: Sequence[OfferEvidence], supplier: Supplier | None = None
) -> RoleAssessment:
    offered = _offer_role(offers)
    registered = (
        RoleAssessment(CompanyRole.UNKNOWN) if supplier is None else registry_role(supplier)
    )
    if offered.role == CompanyRole.UNKNOWN:
        return registered if registered.role != CompanyRole.UNKNOWN else offered
    if registered.role in (CompanyRole.UNKNOWN, offered.role):
        return offered
    return replace(offered, note=registered.note, conflict=True)
