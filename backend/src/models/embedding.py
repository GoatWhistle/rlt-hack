from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EmbeddingDocument:
    offer_id: UUID
    content_hash: str
    name: str
    brand: str
    article: str
    description: str
    attributes: dict[str, str]


@dataclass(frozen=True, slots=True)
class OfferSearchHit:
    offer_id: UUID
    name: str
    url: str
    supplier_id: UUID | None
    similarity: float
