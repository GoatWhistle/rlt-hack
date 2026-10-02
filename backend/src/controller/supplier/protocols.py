from typing import Protocol
from uuid import UUID

from src.models.archive_purchase import ArchivePurchase
from src.models.supplier_profile import SupplierProfile


class SupplierProfiles(Protocol):
    async def get(self, supplier_id: UUID) -> SupplierProfile: ...

    async def purchase(self, supplier_id: UUID, lot_id: str) -> ArchivePurchase: ...
