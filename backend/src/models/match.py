from dataclasses import dataclass

from src.models.candidate import SupplierCandidate
from src.models.offer_summary import OfferSummary
from src.models.query_item import QueryItem
from src.models.search_result import PipelineInfo, SearchWarning


@dataclass(frozen=True, slots=True)
class MatchOutcome:
    candidates: tuple[SupplierCandidate, ...]
    channels: tuple[str, ...]
    warnings: tuple[SearchWarning, ...] = ()
    offers: tuple[OfferSummary, ...] = ()


@dataclass(frozen=True, slots=True)
class MatchReport:
    items: tuple[QueryItem, ...]
    candidates: tuple[SupplierCandidate, ...]
    pipeline: PipelineInfo
    warnings: tuple[SearchWarning, ...] = ()
    offers: tuple[OfferSummary, ...] = ()
