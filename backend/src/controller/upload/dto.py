from typing import Annotated
from uuid import UUID

from pydantic import ConfigDict, Field, StringConstraints

from src.controller.http.schema import CamelModel, UtcDateTime
from src.controller.search.dto import SearchResponseDto
from src.models.enums import IssueCode, LotStatus
from src.models.procurement import LOT_ID_MAX_LENGTH

MAX_SELECTED_LOTS = 500


class CountsDto(CamelModel):
    ready: int
    needs_check: int
    no_candidates: int
    failed: int


class UploadSummaryDto(CamelModel):
    id: UUID
    file_name: str
    created_at: UtcDateTime
    total: int
    processed: int
    counts: CountsDto
    rejected: int


class UploadListDto(CamelModel):
    uploads: list[UploadSummaryDto]


class LotSummaryDto(CamelModel):
    id: str
    title: str
    subject: str | None
    customer_inn: str | None
    publish_date: str | None
    start_price: float | None
    status: LotStatus
    products: int
    candidates: int
    search_id: UUID | None


class IssueDto(CamelModel):
    row: int
    code: IssueCode
    value: str | None


class UploadDetailDto(UploadSummaryDto):
    lots: list[LotSummaryDto]
    issues: list[IssueDto]


class LotResultDto(CamelModel):
    lot: LotSummaryDto
    search: SearchResponseDto | None


class LotDetailDto(LotResultDto):
    upload: UploadSummaryDto


class LotResultsDto(CamelModel):
    results: list[LotResultDto]


class ResultsRequestDto(CamelModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    lot_ids: list[Annotated[str, StringConstraints(max_length=LOT_ID_MAX_LENGTH)]] = Field(
        max_length=MAX_SELECTED_LOTS
    )
