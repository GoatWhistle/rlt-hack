from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EmbeddingDocument:
    offer_id: UUID
    content_hash: str
    name: str
    brand: str
    article: str
    description: str
    attributes: Mapping[str, str] = field(hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))


@dataclass(frozen=True, slots=True)
class OfferSearchHit:
    offer_id: UUID
    name: str
    url: str
    supplier_id: UUID | None
    similarity: float
