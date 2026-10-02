"""Сборка бизнес-моделей из разобранных записей Пульса цен."""

from datetime import UTC, datetime
from uuid import UUID

from src.adapter.supplier import identity
from src.adapter.supplier.pulscen_web import parsing
from src.models.catalog.offer import Offer
from src.models.catalog.source import Source
from src.models.catalog.supplier import Supplier
from src.models.enums import ItemType, SupplierRole, VerificationStatus


class ModelBuilder:
    def __init__(self, source: Source) -> None:
        self._source = source

    def supplier_id(self, company_id: str) -> UUID:
        return identity.supplier_id(None, self._source.source_id, f"company:{company_id}")

    def supplier(self, company: parsing.ListedCompany) -> Supplier:
        return Supplier(
            supplier_id=self.supplier_id(company.company_id),
            name=company.name,
            region=company.address,
            website=company.website,
            identity_status=VerificationStatus.UNVERIFIED,
            identity_evidence_url=self._source.base_url,
        )

    def seller_supplier(self, seller: parsing.ProductSeller) -> Supplier:
        return Supplier(
            supplier_id=self.supplier_id(seller.company_id),
            name=seller.name or f"Компания {seller.company_id}",
            identity_status=VerificationStatus.UNVERIFIED,
            identity_evidence_url=self._source.base_url,
        )

    def offer(self, product: parsing.ListedProduct, seller: parsing.ProductSeller | None) -> Offer:
        observed_at = datetime.now(UTC)
        attributes = {"price_kind": "listing"} if product.price is not None else {}
        return Offer(
            offer_id=identity.offer_id(self._source.source_id, product.external_id),
            source_id=self._source.source_id,
            external_id=product.external_id,
            url=product.url,
            name=product.name,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
            supplier_id=self.supplier_id(seller.company_id) if seller else None,
            seller_status=VerificationStatus.UNVERIFIED,
            evidence_url=product.url if seller else "",
            item_type=ItemType.GOODS,
            price=product.price,
            currency=product.currency,
            availability=product.availability,
            supplier_role=SupplierRole.UNKNOWN,
            attributes=attributes,
            content_hash=identity.offer_content_hash(
                name=product.name, item_type=str(ItemType.GOODS), attributes=attributes
            ),
        )
