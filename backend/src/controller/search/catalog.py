from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.controller.search.protocols import CatalogSearching
from src.models.enums import ItemType

router = APIRouter(prefix="/v1/catalog")


class CatalogQuery(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=50, ge=1, le=100)
    regions: list[str] = Field(default_factory=list, max_length=100)
    item_type: ItemType | None = None


class CatalogHit(BaseModel):
    offer_id: UUID
    supplier_id: UUID | None
    similarity: float


class CatalogResponse(BaseModel):
    offers: list[CatalogHit]


@router.post("/search")
async def search_catalog(body: CatalogQuery, request: Request) -> CatalogResponse:
    catalog: CatalogSearching = request.app.state.catalog_search
    hits = await catalog.search(body.query, body.limit, body.regions, body.item_type)
    return CatalogResponse(
        offers=[CatalogHit.model_validate(hit, from_attributes=True) for hit in hits]
    )
