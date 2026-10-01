import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from http import HTTPStatus
from uuid import UUID, uuid4

import httpx
from pydantic import ValidationError

from src.adapter.client.errors import MlProtocolError, MlServiceError, MlServiceUnavailableError
from src.adapter.client.ml_service.dto import (
    SCHEMA_VERSION,
    CandidateDto,
    RecommendationRequestDto,
    RecommendationResponseDto,
)
from src.adapter.client.ml_service.protocols import SupplierIdentity
from src.models.query_item import SearchRequest
from src.models.retrieval import ChannelHit, ItemHit, RetrievalHits

logger = logging.getLogger(__name__)

CHANNEL = "semantic"
RECOMMENDATIONS_PATH = "/v1/recommendations"
ATTEMPTS = 2
MAX_RESPONSE_BYTES = 1024 * 1024
CANDIDATE_OVERSAMPLING = 4


def utc_now() -> datetime:
    return datetime.now(UTC)


class MlServiceRetriever:
    def __init__(
        self,
        client: httpx.AsyncClient,
        identity: SupplierIdentity,
        timeout_seconds: float = 5.0,
        request_ids: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._client = client
        self._identity = identity
        self._timeout = httpx.Timeout(timeout_seconds)
        self._request_ids = request_ids
        self._clock = clock

    @property
    def channel(self) -> str:
        return CHANNEL

    async def retrieve(self, request: SearchRequest, limit: int) -> RetrievalHits:
        wire = RecommendationRequestDto.from_domain(
            request, limit, self._request_ids(), self._clock()
        )
        response = await self._exchange(wire)
        return await self._hits(response.candidates, request, limit)

    async def _exchange(self, wire: RecommendationRequestDto) -> RecommendationResponseDto:
        body = wire.model_dump_json(by_alias=True)
        reason = ""
        for attempt in range(1, ATTEMPTS + 1):
            try:
                response = await self._client.post(
                    RECOMMENDATIONS_PATH,
                    content=body,
                    headers={"Content-Type": "application/json"},
                    timeout=self._timeout,
                )
            except httpx.TransportError as error:
                reason = type(error).__name__
                logger.warning("ml service attempt %d failed", attempt, exc_info=True)
                continue
            if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
                reason = "not ready"
                continue
            if response.is_error:
                raise MlServiceError(response.status_code)
            if len(response.content) > MAX_RESPONSE_BYTES:
                raise MlProtocolError("response is too large")
            return _parse(response.content, wire.request_id)
        raise MlServiceUnavailableError(reason)

    async def _hits(
        self, candidates: Sequence[CandidateDto], request: SearchRequest, limit: int
    ) -> RetrievalHits:
        ordered = sorted(candidates, key=lambda candidate: candidate.rank)
        ordered = ordered[: limit * CANDIDATE_OVERSAMPLING]
        identities = await self._identity.ids_by_inn([item.supplier_inn for item in ordered])
        known_items = set(request.item_ids)
        hits: list[ChannelHit] = []
        seen: set[UUID] = set()
        for candidate in ordered:
            supplier_id = identities.get(candidate.supplier_inn.strip())
            if supplier_id is None or supplier_id in seen or len(hits) >= limit:
                continue
            seen.add(supplier_id)
            item_ids = dict.fromkeys(i for i in candidate.matched_item_ids if i in known_items)
            items = tuple(ItemHit(item_id, 1.0 / candidate.rank) for item_id in item_ids)
            hits.append(ChannelHit(supplier_id, len(hits) + 1, items))
        return RetrievalHits(CHANNEL, tuple(hits))


def _parse(content: bytes, request_id: UUID) -> RecommendationResponseDto:
    try:
        response = RecommendationResponseDto.model_validate_json(content)
    except ValidationError as error:
        raise MlProtocolError("response does not match the schema") from error
    if response.schema_version.partition(".")[0] != SCHEMA_VERSION.partition(".")[0]:
        raise MlProtocolError(f"unsupported schema version {response.schema_version}")
    if response.request_id != request_id:
        raise MlProtocolError("request id was not echoed")
    return response
