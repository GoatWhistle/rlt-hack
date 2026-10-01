"""Компания-поставщик."""

from dataclasses import dataclass, field
from uuid import UUID

from src.models.enums import SupplierRole, VerificationStatus


@dataclass(frozen=True, slots=True)
class Supplier:
    supplier_id: UUID
    name: str
    # Компания может существовать без известного ИНН: такие записи требуют проверки.
    inn: str | None = None
    kpps: tuple[str, ...] = ()
    region: str = ""
    website: str = ""
    contacts: dict[str, str] = field(default_factory=dict)
    okved_codes: tuple[str, ...] = ()
    identity_status: VerificationStatus = VerificationStatus.UNVERIFIED
    identity_evidence_url: str = ""
    # Роль компании на рынке и её основание: заполняет обогащение по реестру.
    role: SupplierRole = SupplierRole.UNKNOWN
    role_evidence: str = ""
