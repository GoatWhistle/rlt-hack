from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from src.adapter.repository.clickhouse.search_archive.query_dto import FrozenDto
from src.adapter.repository.errors import CorruptRecordError
from src.models.enums import IssueCode, LotStatus
from src.models.errors import DomainError
from src.models.lot_result import LotResult
from src.models.procurement import RowIssue

PAYLOAD_VERSION = 3
READABLE_VERSIONS = frozenset({PAYLOAD_VERSION})


class IssueDto(FrozenDto):
    row: int
    code: IssueCode
    value: str


ISSUES = TypeAdapter(tuple[IssueDto, ...])


class LotResultDto(FrozenDto):
    payload_version: int = PAYLOAD_VERSION
    lot_id: str
    processed_at: datetime
    status: LotStatus
    search_id: UUID | None = None
    products: int = 0
    candidates: int = 0

    @classmethod
    def from_domain(cls, result: LotResult) -> Self:
        return cls(
            lot_id=result.lot_id,
            processed_at=result.processed_at,
            status=result.status,
            search_id=result.search_id,
            products=result.products,
            candidates=result.candidates,
        )

    def to_domain(self) -> LotResult:
        return LotResult(
            lot_id=self.lot_id,
            processed_at=self.processed_at,
            status=self.status,
            search_id=self.search_id,
            products=self.products,
            candidates=self.candidates,
        )


def encode_lot_result(result: LotResult) -> str:
    return LotResultDto.from_domain(result).model_dump_json()


def decode_lot_result(payload: str) -> LotResult:
    try:
        dto = LotResultDto.model_validate_json(payload)
        if dto.payload_version not in READABLE_VERSIONS:
            raise CorruptRecordError("lot result", f"payload version {dto.payload_version}")
        return dto.to_domain()
    except (ValidationError, DomainError) as error:
        raise CorruptRecordError("lot result", type(error).__name__) from error


def encode_issues(issues: tuple[RowIssue, ...]) -> str:
    dtos = tuple(IssueDto(row=item.row, code=item.code, value=item.value) for item in issues)
    return ISSUES.dump_json(dtos).decode("utf-8")


def decode_issues(payload: str) -> tuple[RowIssue, ...]:
    if not payload:
        return ()
    try:
        return tuple(
            RowIssue(item.row, item.code, item.value) for item in ISSUES.validate_json(payload)
        )
    except (ValidationError, DomainError) as error:
        raise CorruptRecordError("upload issues", type(error).__name__) from error
