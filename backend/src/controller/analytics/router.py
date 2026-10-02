from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from src.controller.analytics import mapper
from src.controller.analytics.dto import (
    AnalyticsSourcesDto,
    CategoriesDto,
    OverviewDto,
    QualityDto,
    RecordsDto,
    RunsDto,
)
from src.controller.analytics.protocols import CatalogAnalytics
from src.controller.http.middleware.caching import uncached
from src.controller.http.response.openapi import errors
from src.controller.http.state import Services, services
from src.models.analytics.filters import AnalyticsFilters
from src.models.analytics.records import RecordProblem, RecordQuery
from src.models.enums import SourceType

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

RECORD_LIMIT = 100
REGION_LIMIT = 64
CATEGORY_LIMIT = 16
UNAVAILABLE = errors(HTTPStatus.SERVICE_UNAVAILABLE)


async def analytics(found: Annotated[Services, Depends(services)]) -> CatalogAnalytics:
    return found.analytics


async def filters(
    source_id: Annotated[UUID | None, Query(alias="sourceId")] = None,
    source_type: Annotated[SourceType | None, Query(alias="sourceType")] = None,
    region: Annotated[str | None, Query(max_length=REGION_LIMIT)] = None,
) -> AnalyticsFilters:
    return AnalyticsFilters(
        source_id=source_id, source_type=source_type, region=(region or "").strip() or None
    )


Service = Annotated[CatalogAnalytics, Depends(analytics)]
Scope = Annotated[AnalyticsFilters, Depends(filters)]


@router.get("/overview", responses=UNAVAILABLE)
async def get_overview(service: Service, scope: Scope, response: Response) -> OverviewDto:
    uncached(response)
    return mapper.to_overview(await service.view(scope))


@router.get("/categories", responses=UNAVAILABLE)
async def get_categories(service: Service, scope: Scope, response: Response) -> CategoriesDto:
    uncached(response)
    return mapper.to_categories(await service.view(scope))


@router.get("/quality", responses=UNAVAILABLE)
async def get_quality(service: Service, scope: Scope, response: Response) -> QualityDto:
    uncached(response)
    return mapper.to_quality(await service.view(scope))


@router.get("/sources", responses=UNAVAILABLE)
async def get_sources(service: Service, scope: Scope, response: Response) -> AnalyticsSourcesDto:
    uncached(response)
    return mapper.to_sources(await service.view(scope))


@router.get("/runs", responses=UNAVAILABLE)
async def get_runs(service: Service, scope: Scope, response: Response) -> RunsDto:
    uncached(response)
    return mapper.to_runs(await service.view(scope))


@router.get("/records", responses=UNAVAILABLE)
async def get_records(
    service: Service,
    scope: Scope,
    response: Response,
    category: Annotated[str | None, Query(max_length=CATEGORY_LIMIT)] = None,
    problem: RecordProblem | None = None,
    limit: Annotated[int, Query(ge=1, le=RECORD_LIMIT)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RecordsDto:
    uncached(response)
    query = RecordQuery(
        category=(category or "").strip() or None, problem=problem, limit=limit, offset=offset
    )
    return mapper.to_records(await service.records(scope, query))
