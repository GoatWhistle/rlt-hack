"""Опубликованная позиция каталога СТЕ, независимая от продавцов и оферт."""

from dataclasses import dataclass, field
from uuid import UUID

from src.models.enums import ItemType


@dataclass(frozen=True, slots=True)
class Product:
    product_id: UUID
    source_id: UUID
    external_id: str
    url: str
    name: str
    description: str = ""
    item_type: ItemType = ItemType.UNKNOWN
    category_id: str = ""
    category_path: tuple[str, ...] = ()
    classifier_codes: dict[str, str] = field(default_factory=dict)
    attributes: dict[str, str] = field(default_factory=dict)
    unit: str = ""
    brand: str = ""
    manufacturer: str = ""
    country: str = ""
    image_urls: tuple[str, ...] = ()
    raw_json: str = ""
    content_hash: str = ""
