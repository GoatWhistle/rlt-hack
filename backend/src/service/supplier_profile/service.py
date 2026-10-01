import asyncio
from uuid import UUID

from src.models.supplier_profile import SupplierProfile
from src.service.errors import SupplierNotFoundError
from src.service.supplier_profile.protocols import OfferCatalog, SupplierDirectory
from src.service.supplier_search.assembly.role import RoleResolver

PROFILE_OFFERS = 50


class SupplierProfileService:
    def __init__(
        self,
        directory: SupplierDirectory,
        offers: OfferCatalog,
        roles: RoleResolver,
        offers_per_supplier: int = PROFILE_OFFERS,
    ) -> None:
        self._directory = directory
        self._offers = offers
        self._roles = roles
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
        role, role_evidence = self._roles.resolve(cards)
        return SupplierProfile(
            supplier=supplier,
            role=role,
            offers=cards,
            role_evidence=role_evidence,
        )
