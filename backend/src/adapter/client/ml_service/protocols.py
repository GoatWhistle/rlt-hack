from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID


class SupplierIdentity(Protocol):
    async def ids_by_inn(self, inns: Sequence[str]) -> Mapping[str, UUID]: ...
