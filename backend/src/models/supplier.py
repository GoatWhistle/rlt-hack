"""Компания-поставщик."""

from dataclasses import dataclass, field
from uuid import UUID

from src.models.enums import VerificationStatus


@dataclass(frozen=True, slots=True)
class Supplier:
    supplier_id: UUID
    name: str
    # Компания может существовать без известного ИНН: такие записи требуют проверки.
    inn: str | None = None
    kpps: tuple[str, ...] = ()
    legal_status: str = "unknown"
    region: str = ""
    website: str = ""
    contacts: dict[str, str] = field(default_factory=dict)
    okved_codes: tuple[str, ...] = ()
    identity_status: VerificationStatus = VerificationStatus.UNVERIFIED
    identity_evidence_url: str = ""
