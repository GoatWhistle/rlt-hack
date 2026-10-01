from dataclasses import dataclass


@dataclass(frozen=True)
class SupplierCandidate:
    inn: str
    category: str
    profile: str
    score: float
    similarity: float
