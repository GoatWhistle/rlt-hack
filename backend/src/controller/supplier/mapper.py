from uuid import UUID

from src.controller.http.schema import plain_decimal
from src.controller.search.mapper import contacts_dto, source_dto
from src.controller.supplier.dto import ArchivePurchaseDto, OfferDto, SupplierProfileDto
from src.models.archive_purchase import ArchivePurchase
from src.models.offer_evidence import OfferEvidence
from src.models.supplier_profile import SupplierProfile
from src.service.errors import SupplierNotFoundError


def parse_supplier_id(raw: str) -> UUID:
    try:
        return UUID(raw)
    except ValueError as error:
        raise SupplierNotFoundError from error


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
        role_basis=profile.role_context.basis,
        role_product=profile.role_context.product or None,
        role_note=profile.role_context.note or None,
        role_conflict=profile.role_context.conflict,
        contacts=contacts_dto(supplier),
        offers=[offer_dto(card) for card in profile.offers],
    )


def to_purchase(purchase: ArchivePurchase) -> ArchivePurchaseDto:
    return ArchivePurchaseDto(
        supplier_inn=purchase.supplier_inn,
        lot_id=purchase.lot_id,
        title=purchase.title,
        published_at=purchase.published.isoformat(),
        outcome=purchase.outcome,
        category=purchase.category,
        customer_inn=purchase.customer_inn or None,
        source_system=purchase.source_system,
        products=list(purchase.products),
        snapshot=purchase.snapshot,
    )
