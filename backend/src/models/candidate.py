from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import UUID

from src.models.enums import CandidateStatus, CheckReason, CompanyRole, HighlightCode, MatchBasis
from src.models.errors import InvalidCandidateError, InvalidMatchError
from src.models.evidence import Evidence
from src.models.purchase import PurchaseSummary
from src.models.scoring import ScoreBreakdown
from src.models.supplier import Supplier

EVIDENCED_BASES = frozenset({MatchBasis.STOCK, MatchBasis.CATALOG})


@dataclass(frozen=True, slots=True)
class ProductMatch:
    item_id: str
    basis: MatchBasis
    offer_id: UUID | None = None
    evidence: Evidence | None = None

    def __post_init__(self) -> None:
        if not self.item_id:
            raise InvalidMatchError("item id is empty")
        if self.basis in EVIDENCED_BASES and (self.offer_id is None or self.evidence is None):
            raise InvalidMatchError(f"{self.basis} needs an offer and its evidence")


@dataclass(frozen=True, slots=True)
class Highlight:
    code: HighlightCode
    params: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))


@dataclass(frozen=True, slots=True)
class SupplierCandidate:
    supplier: Supplier
    role: CompanyRole
    status: CandidateStatus
    score: ScoreBreakdown
    rank: int
    role_evidence: Evidence | None = None
    check_reasons: tuple[CheckReason, ...] = ()
    matches: tuple[ProductMatch, ...] = ()
    history: PurchaseSummary = field(default_factory=PurchaseSummary.empty)
    highlights: tuple[Highlight, ...] = ()

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise InvalidCandidateError("ranks start at 1")
        recommended = self.status == CandidateStatus.RECOMMENDED
        if recommended == bool(self.check_reasons):
            raise InvalidCandidateError("recommended exactly when nothing needs checking")
        if len(set(self.check_reasons)) != len(self.check_reasons):
            raise InvalidCandidateError("check reasons repeat")
        matched = [match.item_id for match in self.matches]
        if len(set(matched)) != len(matched):
            raise InvalidCandidateError("one match per item")

    @property
    def supplier_id(self) -> UUID:
        return self.supplier.supplier_id

    @property
    def matched_item_ids(self) -> frozenset[str]:
        return frozenset(match.item_id for match in self.matches)
