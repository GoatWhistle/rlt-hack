from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import ValidationError

from src.adapter.repository.clickhouse.search_archive.candidate_dto import (
    EvidenceDto,
    HighlightDto,
    HistoryDto,
    MatchDto,
    ScoreDto,
    SupplierDto,
)
from src.adapter.repository.clickhouse.search_archive.query_dto import (
    FrozenDto,
    QueryDto,
    QueryItemDto,
)
from src.adapter.repository.errors import CorruptRecordError
from src.models.candidate import SupplierCandidate
from src.models.enums import CandidateStatus, CheckReason, CompanyRole, WarningCode
from src.models.errors import DomainError
from src.models.search_result import PipelineInfo, SearchResult, SearchWarning

PAYLOAD_VERSION = 1
READABLE_VERSIONS = frozenset({1})


class CandidateDto(FrozenDto):
    supplier: SupplierDto
    role: CompanyRole
    status: CandidateStatus
    score: ScoreDto
    rank: int
    role_evidence: EvidenceDto | None
    check_reasons: tuple[CheckReason, ...]
    matches: tuple[MatchDto, ...]
    history: HistoryDto
    highlights: tuple[HighlightDto, ...]

    @classmethod
    def from_domain(cls, candidate: SupplierCandidate) -> Self:
        return cls(
            supplier=SupplierDto.from_domain(candidate.supplier),
            role=candidate.role,
            status=candidate.status,
            score=ScoreDto.from_domain(candidate.score),
            rank=candidate.rank,
            role_evidence=EvidenceDto.maybe(candidate.role_evidence),
            check_reasons=candidate.check_reasons,
            matches=tuple(MatchDto.from_domain(match) for match in candidate.matches),
            history=HistoryDto.from_domain(candidate.history),
            highlights=tuple(HighlightDto.from_domain(item) for item in candidate.highlights),
        )

    def to_domain(self) -> SupplierCandidate:
        evidence = None if self.role_evidence is None else self.role_evidence.to_domain()
        return SupplierCandidate(
            supplier=self.supplier.to_domain(),
            role=self.role,
            status=self.status,
            score=self.score.to_domain(),
            rank=self.rank,
            role_evidence=evidence,
            check_reasons=self.check_reasons,
            matches=tuple(match.to_domain() for match in self.matches),
            history=self.history.to_domain(),
            highlights=tuple(item.to_domain() for item in self.highlights),
        )


class WarningDto(FrozenDto):
    code: WarningCode
    subject: str


class PipelineDto(FrozenDto):
    version: str
    channels: tuple[str, ...]
    as_of: datetime

    @classmethod
    def from_domain(cls, pipeline: PipelineInfo) -> Self:
        return cls(version=pipeline.version, channels=pipeline.channels, as_of=pipeline.as_of)

    @classmethod
    def maybe(cls, pipeline: PipelineInfo | None) -> Self | None:
        return None if pipeline is None else cls.from_domain(pipeline)

    def to_domain(self) -> PipelineInfo:
        return PipelineInfo(self.version, self.channels, self.as_of)


class SearchResultDto(FrozenDto):
    payload_version: int = PAYLOAD_VERSION
    search_id: UUID
    query: QueryDto
    items: tuple[QueryItemDto, ...]
    candidates: tuple[CandidateDto, ...]
    pipeline: PipelineDto
    created_at: datetime
    warnings: tuple[WarningDto, ...]

    @classmethod
    def from_domain(cls, result: SearchResult) -> Self:
        return cls(
            search_id=result.search_id,
            query=QueryDto.from_domain(result.query),
            items=tuple(QueryItemDto.from_domain(item) for item in result.items),
            candidates=tuple(CandidateDto.from_domain(item) for item in result.candidates),
            pipeline=PipelineDto.from_domain(result.pipeline),
            created_at=result.created_at,
            warnings=tuple(
                WarningDto(code=item.code, subject=item.subject) for item in result.warnings
            ),
        )

    def to_domain(self) -> SearchResult:
        return SearchResult(
            search_id=self.search_id,
            query=self.query.to_domain(),
            items=tuple(item.to_domain() for item in self.items),
            candidates=tuple(item.to_domain() for item in self.candidates),
            pipeline=self.pipeline.to_domain(),
            created_at=self.created_at,
            warnings=tuple(SearchWarning(item.code, item.subject) for item in self.warnings),
        )


def encode_result(result: SearchResult) -> str:
    return SearchResultDto.from_domain(result).model_dump_json()


def decode_result(payload: str) -> SearchResult:
    try:
        dto = SearchResultDto.model_validate_json(payload)
        if dto.payload_version not in READABLE_VERSIONS:
            raise CorruptRecordError("search", f"payload version {dto.payload_version}")
        return dto.to_domain()
    except (ValidationError, DomainError) as error:
        raise CorruptRecordError("search", type(error).__name__) from error
