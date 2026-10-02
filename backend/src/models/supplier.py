from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from urllib.parse import urlsplit
from uuid import UUID

from src.models.enums import NameSource, SupplierRole, VerificationStatus
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
    # Роль компании на рынке и её основание: заполняет обогащение по реестру.
    role: SupplierRole = SupplierRole.UNKNOWN
    role_evidence: str = ""
    name_source: NameSource = NameSource.SOURCE

    def __post_init__(self) -> None:
        object.__setattr__(self, "contacts", MappingProxyType(dict(self.contacts)))

    @property
    def has_valid_inn(self) -> bool:
        return self.inn is not None and is_valid_inn(self.inn)

    def without_operator_contacts(self, operators: frozenset[str]) -> "Supplier":
        website = self.website if not _belongs(_host(self.website), operators) else ""
        contacts = {
            key: value
            for key, value in self.contacts.items()
            if not (key == "email" and _belongs(value.rpartition("@")[2].lower(), operators))
        }
        if website == self.website and len(contacts) == len(self.contacts):
            return self
        return replace(self, website=website, contacts=contacts)


def _host(url: str) -> str:
    try:
        return (urlsplit(url.strip()).hostname or "").lower()
    except ValueError:
        return ""


def operator_host(url: str) -> str:
    return _host(url).removeprefix("www.")


def _belongs(host: str, operators: frozenset[str]) -> bool:
    plain = host.removeprefix("www.")
    return bool(plain) and any(
        plain == operator or plain.endswith(f".{operator}") for operator in operators
    )
