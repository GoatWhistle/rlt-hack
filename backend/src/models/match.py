from dataclasses import dataclass

from src.models.candidate import SupplierCandidate
from src.models.query_item import QueryItem
from src.models.search_result import PipelineInfo, SearchWarning


@dataclass(frozen=True, slots=True)
class MatchOutcome:
    candidates: tuple[SupplierCandidate, ...]
    channels: tuple[str, ...]
    warnings: tuple[SearchWarning, ...] = ()
    novelty_set: str = ""
    models: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class MatchReport:
    items: tuple[QueryItem, ...]
    candidates: tuple[SupplierCandidate, ...]
    pipeline: PipelineInfo
    warnings: tuple[SearchWarning, ...] = ()
