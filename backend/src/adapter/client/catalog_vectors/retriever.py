import asyncio
from uuid import UUID

import httpx
from pydantic import BaseModel, Field, ValidationError

from src.adapter.client.errors import MlProtocolError, MlServiceError
from src.adapter.repository.clickhouse.search.retrieval.tally import HitTally
from src.models.enums import RetrievalChannel
from src.models.ranking.retrieval import RetrievalHits
from src.models.search.query_item import QueryItem, SearchRequest


class OfferHitDto(BaseModel):
    offer_id: UUID
    supplier_id: UUID | None
    similarity: float = Field(ge=-1, le=1, allow_inf_nan=False)


class OfferResponseDto(BaseModel):
    offers: tuple[OfferHitDto, ...] = Field(max_length=100)


class CatalogVectorRetriever:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._slots = asyncio.Semaphore(2)

    @property
    def channel(self) -> str:
        return RetrievalChannel.CATALOG_VECTOR

    async def retrieve(self, request: SearchRequest, limit: int) -> RetrievalHits:
        responses = await asyncio.gather(*(self._search(item, request) for item in request.items))
        tally = HitTally(accumulate=False)
        for item, offers in zip(request.items, responses, strict=True):
            for offer in offers:
                if offer.supplier_id is not None and offer.similarity > 0:
                    tally.add_offer(
                        offer.supplier_id, item.item_id, offer.offer_id, offer.similarity
                    )
        return tally.hits(self.channel, limit)

    async def _search(self, item: QueryItem, request: SearchRequest) -> tuple[OfferHitDto, ...]:
        async with self._slots:
            response = await self._client.post(
                "/v1/catalog/search",
                json={
                    "query": item.name,
                    "limit": 100,
                    "regions": list(request.query.filters.regions),
                    "item_type": request.query.filters.item_type,
                },
            )
        if response.is_error:
            raise MlServiceError(response.status_code)
        if len(response.content) > 1024 * 1024:
            raise MlProtocolError("catalog response is too large")
        try:
            return OfferResponseDto.model_validate_json(response.content).offers
        except ValidationError as error:
            raise MlProtocolError("invalid catalog vector response") from error
