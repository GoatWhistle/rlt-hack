from dataclasses import dataclass, field


@dataclass(frozen=True)
class SupplierCatalogOffer:
    name: str
    url: str
    observed_at: str


@dataclass(frozen=True)
class SupplierPurchase:
    lot_id: str
    title: str
    publish_date: str
    customer_inn: str
    source_system: str
    product_names: list[str]
    is_winner: bool


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
    purchases: list[SupplierPurchase] = field(default_factory=list)
    category_lots: int | None = None
    category_wins: int | None = None
    category_name: str = ""
    ranking_reasons: list[str] = field(default_factory=list)
    registered_region: str = ""
    matched_category_count: int = 0
