from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from src.models.catalog.supplier import Supplier
from src.models.company.offer_evidence import OfferEvidence


class SupplierDirectory(Protocol):
    async def get_many(self, supplier_ids: Sequence[UUID]) -> Mapping[UUID, Supplier]: ...


class OfferCatalog(Protocol):
    async def current_for(
        self, supplier_ids: Sequence[UUID], per_supplier: int
    ) -> Mapping[UUID, tuple[OfferEvidence, ...]]: ...
