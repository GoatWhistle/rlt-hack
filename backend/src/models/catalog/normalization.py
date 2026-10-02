from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class Normalization:
    name: str = ""
    key: str = ""
    brand: str = ""
    article: str = ""
    attributes: Mapping[str, str] = field(default_factory=dict, hash=False)
    unit_code: str = ""
    unit_name: str = ""
    price_per_unit: Decimal | None = None
    price_unit_code: str = ""
    currency: str = ""
    algorithm_version: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))
