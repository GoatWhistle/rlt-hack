from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EmbeddingDocument:
    """Поля позиции, попадающие в вектор, и хеш именно этого набора.

    `content_hash` считает хранилище по всем перечисленным полям, а не только по
    смысловым полям предложения: иначе смена региона или названия компании не
    пересчитала бы вектор, в который она входит.
    """

    offer_id: UUID
    content_hash: str
    name: str
    normalized_name: str = ""
    brand: str = ""
    article: str = ""
    item_type: str = ""
    unit: str = ""
    source_category: str = ""
    okpd2_code: str = ""
    rubric_name: str = ""
    supplier_role: str = ""
    supplier_name: str = ""
    region: str = ""
    address: str = ""
    description: str = ""
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OfferSearchHit:
    offer_id: UUID
    name: str
    url: str
    supplier_id: UUID | None
    similarity: float
