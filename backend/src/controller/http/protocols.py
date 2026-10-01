from typing import Protocol

from src.controller.health.protocols import ReadinessChecking
from src.controller.search.protocols import SupplierSearching
from src.controller.supplier.protocols import SupplierProfiles
from src.controller.upload.protocols import ProcurementUploads


class ServiceProvider(Protocol):
    async def supplier_search(self) -> SupplierSearching: ...

    async def supplier_profiles(self) -> SupplierProfiles: ...

    async def procurement_uploads(self) -> ProcurementUploads: ...

    async def health(self) -> ReadinessChecking: ...

    async def aclose(self) -> None: ...
