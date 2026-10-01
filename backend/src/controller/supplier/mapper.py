from uuid import UUID

from src.controller.http.schema import plain_decimal
from src.controller.search.mapper import contacts_dto, source_dto
from src.controller.supplier.dto import OfferDto, SupplierProfileDto
from src.models.offer_evidence import OfferEvidence
from src.models.supplier_profile import SupplierProfile
from src.service.errors import SupplierNotFoundError


def parse_supplier_id(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError as error:
        raise SupplierNotFoundError(raw) from error


def offer_dto(card: OfferEvidence) -> OfferDto:
    offer = card.offer
    return OfferDto(
        id=offer.offer_id,
        name=offer.name,
        price=None if offer.price is None else plain_decimal(offer.price),
        currency=offer.currency,
        unit=offer.unit,
        availability=offer.availability,
        source=source_dto(card.evidence),
    )


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
        offers=[offer_dto(card) for card in profile.offers],
    )
