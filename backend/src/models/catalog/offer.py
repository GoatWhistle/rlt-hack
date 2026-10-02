from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType
from uuid import UUID

from src.models.catalog.classification import Classification
from src.models.catalog.normalization import Normalization
from src.models.enums import Availability, ItemType, SupplierRole, VerificationStatus


@dataclass(frozen=True, slots=True)
class Offer:
    offer_id: UUID
    source_id: UUID
    external_id: str
    url: str
    name: str
    first_seen_at: datetime
    last_seen_at: datetime
    supplier_id: UUID | None = None
    seller_status: VerificationStatus = VerificationStatus.UNVERIFIED
    evidence_url: str = ""
    description: str = ""
    item_type: ItemType = ItemType.UNKNOWN
    brand: str = ""
    article: str = ""
    attributes: Mapping[str, str] = field(default_factory=dict, hash=False)
    source_category: str = ""
    okpd2_code: str = ""
    price: Decimal | None = None
    currency: str = ""
    unit: str = ""
    availability: Availability = Availability.UNKNOWN
    supplier_role: SupplierRole = SupplierRole.UNKNOWN
    role_evidence_text: str = ""
    content_hash: str = ""
    normalization: Normalization | None = None
    classification: Classification | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))
