from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import UUID

from src.models.enums import VerificationStatus
from src.models.inn import is_valid_inn


@dataclass(frozen=True, slots=True)
class Supplier:
    supplier_id: UUID
    name: str
    inn: str | None = None
    kpps: tuple[str, ...] = ()
    region: str = ""
    website: str = ""
    contacts: Mapping[str, str] = field(default_factory=dict, hash=False)
    okved_codes: tuple[str, ...] = ()
    identity_status: VerificationStatus = VerificationStatus.UNVERIFIED
    identity_evidence_url: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "contacts", MappingProxyType(dict(self.contacts)))

    @property
    def has_valid_inn(self) -> bool:
        return self.inn is not None and is_valid_inn(self.inn)
