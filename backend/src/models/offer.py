"""Исходное предложение товара, работы или услуги."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.models.classification import Classification
from src.models.enums import Availability, ItemType, SupplierRole, VerificationStatus
from src.models.normalization import Normalization


@dataclass(frozen=True, slots=True)
class Offer:
    offer_id: UUID
    source_id: UUID
    # Внешний ID продавца или канонический URL с идентификатором варианта.
    external_id: str
    url: str
    name: str
    first_seen_at: datetime
    last_seen_at: datetime
    # Продавец известен не всегда: принадлежность подтверждается отдельно.
    supplier_id: UUID | None = None
    seller_status: VerificationStatus = VerificationStatus.UNVERIFIED
    # Где подтверждено, что продавец — именно эта компания.
    evidence_url: str = ""
    description: str = ""
    item_type: ItemType = ItemType.UNKNOWN
    brand: str = ""
    article: str = ""
    attributes: dict[str, str] = field(default_factory=dict)
    source_category: str = ""
    okpd2_code: str = ""
    price: Decimal | None = None
    currency: str = ""
    unit: str = ""
    availability: Availability = Availability.UNKNOWN
    supplier_role: SupplierRole = SupplierRole.UNKNOWN
    role_evidence_text: str = ""
    # Хеш полей, влияющих на смысл: цена в него не входит.
    content_hash: str = ""
    # Производные значения: их считают нормализатор и классификатор, а не адаптер.
    # На хеш содержимого они не влияют — исходник остаётся исходником.
    normalization: Normalization | None = None
    classification: Classification | None = None
