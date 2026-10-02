from uuid import UUID

from src.controller.http.schema import CamelModel
from src.controller.search.dto import ContactsDto, OfferDto, SourceDto
from src.models.enums import CompanyRole, VerificationStatus


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
