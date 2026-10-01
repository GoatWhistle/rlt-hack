from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.models.candidate import SupplierCandidate, ranking_problem
from src.models.enums import CandidateStatus, Locale, WarningCode
from src.models.errors import InvalidSearchResultError
from src.models.query_item import QueryItem
from src.models.search import SearchQuery, SearchText


@dataclass(frozen=True, slots=True)
class SearchWarning:
    code: WarningCode
    subject: str = ""


@dataclass(frozen=True, slots=True)
class PipelineInfo:
    version: str
    channels: tuple[str, ...]
    as_of: datetime


@dataclass(frozen=True, slots=True)
class SearchResult:
    search_id: UUID
    query: SearchQuery
    items: tuple[QueryItem, ...]
    candidates: tuple[SupplierCandidate, ...]
    pipeline: PipelineInfo
    created_at: datetime
    warnings: tuple[SearchWarning, ...] = ()

    def __post_init__(self) -> None:
        problem = ranking_problem(self.candidates, self.items)
        if problem is not None:
            raise InvalidSearchResultError(problem)
        if len(self.candidates) > self.query.limit.value:
            raise InvalidSearchResultError("more candidates than the limit")

    @property
    def recommended(self) -> int:
        return sum(1 for item in self.candidates if item.status == CandidateStatus.RECOMMENDED)

    def summary(self) -> "SearchSummary":
        return SearchSummary(
            search_id=self.search_id,
            text=self.query.text,
            locale=self.query.locale,
            items=len(self.items),
            candidates=len(self.candidates),
            recommended=self.recommended,
            created_at=self.created_at,
        )


@dataclass(frozen=True, slots=True)
class SearchSummary:
    search_id: UUID
    text: SearchText
    locale: Locale
    items: int
    candidates: int
    recommended: int
    created_at: datetime
