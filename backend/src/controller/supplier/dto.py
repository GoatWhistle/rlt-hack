from uuid import UUID

from src.controller.http.schema import CamelModel
from src.controller.search.dto import ContactsDto, SourceDto
from src.models.enums import Availability, CompanyRole, VerificationStatus


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
