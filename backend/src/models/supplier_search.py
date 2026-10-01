from dataclasses import dataclass, field


@dataclass(frozen=True)
class SupplierCatalogOffer:
    name: str
    url: str
    observed_at: str


@dataclass(frozen=True)
class SupplierCandidate:
    inn: str
    category: str
    profile: str
    score: float
    similarity: float
    history_examples: list[str] = field(default_factory=list)
    history_last_date: str = ""
    name: str = ""
    website: str = ""
    email: str = ""
    phone: str = ""
    identity_url: str = ""
    catalog: list[SupplierCatalogOffer] = field(default_factory=list)
