from datetime import datetime
from typing import Self

from pydantic import TypeAdapter

from src.adapter.repository.clickhouse.search_archive.query_dto import FrozenDto, QueryItemDto
from src.adapter.repository.clickhouse.search_archive.result_dto import CandidateDto, WarningDto
from src.models.enums import IssueCode
from src.models.lot_result import LotResult
from src.models.procurement import RowIssue
from src.models.search_result import SearchWarning

PAYLOAD_VERSION = 1


class IssueDto(FrozenDto):
    row: int
    code: IssueCode
    value: str


ISSUES = TypeAdapter(tuple[IssueDto, ...])


class LotResultDto(FrozenDto):
    payload_version: int = PAYLOAD_VERSION
    lot_id: str
    processed_at: datetime
    items: tuple[QueryItemDto, ...]
    candidates: tuple[CandidateDto, ...]
    warnings: tuple[WarningDto, ...]
    failed: bool

    @classmethod
    def from_domain(cls, result: LotResult) -> Self:
        return cls(
            lot_id=result.lot_id,
            processed_at=result.processed_at,
            items=tuple(QueryItemDto.from_domain(item) for item in result.items),
            candidates=tuple(CandidateDto.from_domain(item) for item in result.candidates),
            warnings=tuple(
                WarningDto(code=item.code, subject=item.subject) for item in result.warnings
            ),
            failed=result.failed,
        )

    def to_domain(self) -> LotResult:
        return LotResult(
            lot_id=self.lot_id,
            processed_at=self.processed_at,
            items=tuple(item.to_domain() for item in self.items),
            candidates=tuple(item.to_domain() for item in self.candidates),
            warnings=tuple(SearchWarning(item.code, item.subject) for item in self.warnings),
            failed=self.failed,
        )


def encode_lot_result(result: LotResult) -> str:
    return LotResultDto.from_domain(result).model_dump_json()


def decode_lot_result(payload: str) -> LotResult:
    return LotResultDto.model_validate_json(payload).to_domain()


def encode_issues(issues: tuple[RowIssue, ...]) -> str:
    dtos = tuple(IssueDto(row=item.row, code=item.code, value=item.value) for item in issues)
    return ISSUES.dump_json(dtos).decode("utf-8")


def decode_issues(payload: str) -> tuple[RowIssue, ...]:
    if not payload:
        return ()
    return tuple(
        RowIssue(item.row, item.code, item.value) for item in ISSUES.validate_json(payload)
    )
