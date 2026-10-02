from uuid import UUID

from src.controller.search.mapper import contacts_dto, offer_dto, source_dto
from src.controller.supplier.dto import SupplierProfileDto
from src.models.offer_summary import OfferSummary
from src.models.supplier_profile import SupplierProfile
from src.service.errors import SupplierNotFoundError


def parse_supplier_id(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError as error:
        raise SupplierNotFoundError from error


def to_profile(profile: SupplierProfile) -> SupplierProfileDto:
    supplier = profile.supplier
    return SupplierProfileDto(
        id=supplier.supplier_id,
        name=supplier.name,
        inn=supplier.inn or "",
        kpps=list(supplier.kpps),
        region=supplier.region,
        identity=supplier.identity_status,
        role=profile.role,
        role_source=source_dto(profile.role_evidence),
        contacts=contacts_dto(supplier),
        offers=[offer_dto(OfferSummary.of(card)) for card in profile.offers],
    )
