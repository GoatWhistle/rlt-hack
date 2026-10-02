from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.models.supplier_search import SupplierCandidate

SCHEMA_VERSION = "1.0"
MAX_LIMIT = 100


class WireModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class NoticeWire(WireModel):
    procedure_name: str = Field(min_length=1, max_length=4000)
    subject: str = ""
    customer_inn: str | None = None
    start_price: str | None = None


class ItemWire(WireModel):
    item_id: str
    name: str


class OptionsWire(WireModel):
    candidate_limit: int = Field(default=20, ge=1, le=MAX_LIMIT)


class RecommendationRequest(WireModel):
    schema_version: str
    request_id: UUID
    as_of: datetime
    notice: NoticeWire
    items: list[ItemWire] = Field(default_factory=list, max_length=100)
    options: OptionsWire = Field(default_factory=OptionsWire)

    @property
    def text(self) -> str:
        names = " ".join(item.name for item in self.items)
        return (self.notice.procedure_name + "\n" + names).strip()[:4000]


class RetrievalWire(WireModel):
    fusion_rank: int
    score: float


class CandidateWire(WireModel):
    supplier_inn: str
    rank: int
    retrieval: RetrievalWire
    matched_item_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class PipelineWire(WireModel):
    pipeline_version: str
    warnings: list[str] = Field(default_factory=list)


class RecommendationResponse(WireModel):
    schema_version: str = SCHEMA_VERSION
    request_id: UUID
    pipeline: PipelineWire
    candidates: list[CandidateWire]


def to_response(
    request: RecommendationRequest, found: list[SupplierCandidate], version: str
) -> RecommendationResponse:
    candidates = [
        CandidateWire(
            supplier_inn=item.inn,
            rank=rank,
            retrieval=RetrievalWire(fusion_rank=rank, score=item.score),
            evidence_refs=[f"category:{item.category}"] if item.category else [],
        )
        for rank, item in enumerate(found, 1)
    ]
    warnings = (
        ["contextIgnored"] if request.notice.customer_inn or request.notice.start_price else []
    )
    return RecommendationResponse(
        request_id=request.request_id,
        pipeline=PipelineWire(pipeline_version=version, warnings=warnings),
        candidates=candidates,
    )
