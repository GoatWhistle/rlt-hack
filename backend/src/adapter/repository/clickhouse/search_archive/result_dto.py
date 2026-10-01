from datetime import datetime
from typing import Self
from uuid import UUID

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
from src.models.candidate import SupplierCandidate
from src.models.enums import CandidateStatus, CheckReason, CompanyRole, WarningCode
from src.models.search_result import PipelineInfo, SearchResult, SearchWarning

PAYLOAD_VERSION = 1


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
        pipeline = result.pipeline
        return cls(
            search_id=result.search_id,
            query=QueryDto.from_domain(result.query),
            items=tuple(QueryItemDto.from_domain(item) for item in result.items),
            candidates=tuple(CandidateDto.from_domain(item) for item in result.candidates),
            pipeline=PipelineDto(
                version=pipeline.version, channels=pipeline.channels, as_of=pipeline.as_of
            ),
            created_at=result.created_at,
            warnings=tuple(
                WarningDto(code=item.code, subject=item.subject) for item in result.warnings
            ),
        )

    def to_domain(self) -> SearchResult:
        pipeline = self.pipeline
        return SearchResult(
            search_id=self.search_id,
            query=self.query.to_domain(),
            items=tuple(item.to_domain() for item in self.items),
            candidates=tuple(item.to_domain() for item in self.candidates),
            pipeline=PipelineInfo(pipeline.version, pipeline.channels, pipeline.as_of),
            created_at=self.created_at,
            warnings=tuple(SearchWarning(item.code, item.subject) for item in self.warnings),
        )


def encode_result(result: SearchResult) -> str:
    return SearchResultDto.from_domain(result).model_dump_json()


def decode_result(payload: str) -> SearchResult:
    return SearchResultDto.model_validate_json(payload).to_domain()
