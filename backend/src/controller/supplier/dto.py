from typing import Literal
from uuid import UUID

from src.controller.http.schema import CamelModel
from src.controller.search.dto import ContactsDto, SourceDto
from src.models.enums import Availability, CompanyRole, PurchaseOutcome, VerificationStatus


class OfferDto(CamelModel):
    id: UUID
    name: str
    price: str | None
    currency: str
    unit: str
    availability: Availability
    source: SourceDto | None


class SupplierProfileDto(CamelModel):
    id: UUID
    name: str
    inn: str
    kpps: list[str]
    region: str
    identity: VerificationStatus
    role: CompanyRole
    role_source: SourceDto | None
    contacts: ContactsDto
    offers: list[OfferDto]


class ArchivePurchaseDto(CamelModel):
    provenance: Literal["procurementArchive"] = "procurementArchive"
    supplier_inn: str
    lot_id: str
    title: str
    published_at: str
    outcome: PurchaseOutcome
    category: str
    customer_inn: str | None
    source_system: str
    products: list[str]
    snapshot: str
