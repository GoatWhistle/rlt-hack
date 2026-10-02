from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import UUID

from src.models.enums import (
    CandidateOrigin,
    CandidateStatus,
    CheckReason,
    CompanyRole,
    HighlightCode,
    MatchBasis,
    Novelty,
    RequirementStatus,
)
from src.models.errors import InvalidCandidateError, InvalidMatchError
from src.models.evidence import Evidence
from src.models.offer_snapshot import OfferSnapshot
from src.models.purchase import PurchaseSummary
from src.models.query_item import QueryItem
from src.models.requirement import RequirementCheck
from src.models.scoring import ScoreBreakdown
from src.models.supplier import Supplier

EVIDENCED_BASES = frozenset({MatchBasis.STOCK, MatchBasis.CATALOG})
CHANNEL_ORIGINS = {
    "lexical": CandidateOrigin.CATALOG,
    "history": CandidateOrigin.HISTORY,
    "semantic": CandidateOrigin.HISTORY,
}


@dataclass(frozen=True, slots=True)
class ProductMatch:
    item_id: str
    basis: MatchBasis
    offer_id: UUID | None = None
    evidence: Evidence | None = None
    offer: OfferSnapshot | None = None
    checks: tuple[RequirementCheck, ...] = ()

    def __post_init__(self) -> None:
        if not self.item_id:
            raise InvalidMatchError("item id is empty")
        if self.basis in EVIDENCED_BASES and (self.offer_id is None or self.evidence is None):
            raise InvalidMatchError(f"{self.basis} needs an offer and its evidence")
        if self.offer is not None and self.offer.offer_id != self.offer_id:
            raise InvalidMatchError("offer snapshot belongs to another offer")
        if self.conflicting and self.basis in EVIDENCED_BASES:
            raise InvalidMatchError("a conflicting offer cannot confirm the item")

    @property
    def conflicting(self) -> bool:
        return any(check.status == RequirementStatus.CONFLICT for check in self.checks)


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
    novelty: Novelty = Novelty.UNKNOWN

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

    @property
    def origins(self) -> tuple[CandidateOrigin, ...]:
        found = {
            CHANNEL_ORIGINS[rank.channel]
            for rank in self.score.channels
            if rank.channel in CHANNEL_ORIGINS
        }
        return tuple(origin for origin in CandidateOrigin if origin in found)


def ranking_problem(
    candidates: Sequence[SupplierCandidate], items: Sequence[QueryItem]
) -> str | None:
    ranks = [candidate.rank for candidate in candidates]
    if ranks != list(range(1, len(ranks) + 1)):
        return "candidate ranks must run 1..n in order"
    suppliers = {candidate.supplier_id for candidate in candidates}
    if len(suppliers) != len(candidates):
        return "a supplier is ranked twice"
    known = {item.item_id for item in items}
    if any(not candidate.matched_item_ids <= known for candidate in candidates):
        return "a match points to an unknown item"
    return None
