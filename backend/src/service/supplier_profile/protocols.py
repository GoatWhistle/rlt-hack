from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from src.models.archive_purchase import ArchivePurchase
from src.models.offer_evidence import OfferEvidence
from src.models.supplier import Supplier


class SupplierDirectory(Protocol):
    async def get_many(self, supplier_ids: Sequence[UUID]) -> Mapping[UUID, Supplier]: ...


class ArchivePurchases(Protocol):
    async def get(self, supplier_id: UUID, lot_id: str) -> ArchivePurchase | None: ...


class OfferCatalog(Protocol):
    async def current_for(
        self, supplier_ids: Sequence[UUID], per_supplier: int
    ) -> Mapping[UUID, tuple[OfferEvidence, ...]]: ...
