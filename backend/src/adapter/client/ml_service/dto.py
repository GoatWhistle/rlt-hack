from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.models.enums import ItemOrigin
from src.models.query_item import QueryItem, SearchRequest

SCHEMA_VERSION = "1.0"
MAX_CANDIDATE_LIMIT = 100
WIRE_ORIGINS = {
    ItemOrigin.TEXT: "notice",
    ItemOrigin.INFERRED: "inferred",
    ItemOrigin.USER: "user",
}


class WireDto(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class NoticeDto(WireDto):
    lot_id: str | None = None
    procedure_name: str
    subject: str = ""
    published_at: datetime | None = None
    start_price: str | None = None
    currency: str = ""
    customer_inn: str | None = None
    is_smp: bool | None = None
    region: str = ""


class ItemDto(WireDto):
    item_id: str
    name: str
    okpd2: str
    item_type: str
    quantity: str | None
    unit: str
    attributes: dict[str, str] = Field(default_factory=dict)
    origin: str
    confidence: float | None = None

    @classmethod
    def from_domain(cls, item: QueryItem) -> Self:
        quantity = item.quantity
        return cls(
            item_id=item.item_id,
            name=item.name,
            okpd2=item.okpd2,
            item_type=str(item.item_type),
            quantity=None if quantity is None else str(quantity.value),
            unit="" if quantity is None else quantity.unit,
            origin=WIRE_ORIGINS[item.origin],
        )


class OptionsDto(WireDto):
    candidate_limit: int
    include_historical_evidence: bool = True


class RecommendationRequestDto(WireDto):
    schema_version: str = SCHEMA_VERSION
    request_id: UUID
    as_of: datetime
    notice: NoticeDto
    items: tuple[ItemDto, ...]
    options: OptionsDto

    @classmethod
    def from_domain(
        cls, request: SearchRequest, limit: int, request_id: UUID, as_of: datetime
    ) -> Self:
        regions = request.query.filters.regions
        context = request.query.context
        price = context.start_price
        return cls(
            request_id=request_id,
            as_of=as_of,
            notice=NoticeDto(
                procedure_name=request.query.text.value,
                region=regions[0] if regions else "",
                customer_inn=context.customer_inn or None,
                start_price=None if price is None else format(price, "f"),
            ),
            items=tuple(ItemDto.from_domain(item) for item in request.items),
            options=OptionsDto(candidate_limit=min(max(limit, 1), MAX_CANDIDATE_LIMIT)),
        )


class RetrievalDto(WireDto):
    dense_rank: int | None = None
    lexical_rank: int | None = None
    fusion_rank: int | None = None
    score: float | None = None


class CandidateDto(WireDto):
    supplier_inn: str
    rank: int = Field(ge=1)
    retrieval: RetrievalDto | None = None
    matched_item_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


class PipelineDto(WireDto):
    pipeline_version: str = ""
    warnings: tuple[str, ...] = ()


class RecommendationResponseDto(WireDto):
    schema_version: str
    request_id: UUID
    pipeline: PipelineDto | None = None
    candidates: tuple[CandidateDto, ...] = ()
