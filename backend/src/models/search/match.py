from dataclasses import dataclass

from src.models.search.candidate import SupplierCandidate
from src.models.search.offer_summary import OfferSummary
from src.models.search.query_item import QueryItem
from src.models.search.search_result import PipelineInfo, SearchWarning


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
