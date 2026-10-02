import asyncio
from uuid import UUID

from src.models.company.company_role import assess_role
from src.models.company.supplier_profile import SupplierProfile
from src.service.errors import SupplierNotFoundError
from src.service.supplier_profile.protocols import OfferCatalog, SupplierDirectory

PROFILE_OFFERS = 50


class SupplierProfileService:
    def __init__(
        self,
        directory: SupplierDirectory,
        offers: OfferCatalog,
        offers_per_supplier: int = PROFILE_OFFERS,
    ) -> None:
        self._directory = directory
        self._offers = offers
        self._offers_per_supplier = offers_per_supplier

    async def get(self, supplier_id: UUID) -> SupplierProfile:
        suppliers, offers = await asyncio.gather(
            self._directory.get_many([supplier_id]),
            self._offers.current_for([supplier_id], self._offers_per_supplier),
        )
        supplier = suppliers.get(supplier_id)
        if supplier is None:
            raise SupplierNotFoundError(supplier_id)
        cards = offers.get(supplier_id, ())
        role = assess_role(cards)
        return SupplierProfile(
            supplier=supplier,
            role=role.role,
            offers=cards,
            role_evidence=role.evidence,
        )
