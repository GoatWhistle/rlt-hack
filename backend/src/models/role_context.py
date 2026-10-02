from dataclasses import dataclass

from src.models.enums import RoleBasis


@dataclass(frozen=True, slots=True)
class RoleContext:
    basis: RoleBasis = RoleBasis.NONE
    product: str = ""
    note: str = ""
    conflict: bool = False
