from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from src.controller.http.error_body import ApiErrorDto
from src.controller.http.locale import request_locale
from src.controller.http.metrics import Metrics
from src.controller.http.state import Services, metrics, services
from src.controller.search.dto import RecentSearchesDto, SearchRequestDto, SearchResponseDto
from src.controller.search.mapper import parse_search_id, to_query, to_response, to_summary
from src.controller.search.observe import log_search_request, report_search
from src.controller.search.protocols import SupplierSearching
from src.models.enums import Locale

RECENT_DEFAULT = 10
RECENT_MAX = 50

router = APIRouter(prefix="/api/searches", tags=["searches"])

ERRORS: dict[int | str, dict[str, object]] = {
    code: {"model": ApiErrorDto} for code in (404, 422, 500, 503, 504)
}


async def searching(found: Annotated[Services, Depends(services)]) -> SupplierSearching:
    return found.supplier_search


@router.post("", status_code=status.HTTP_201_CREATED, responses=ERRORS)
async def create_search(
    payload: SearchRequestDto,
    response: Response,
    locale: Annotated[Locale, Depends(request_locale)],
    service: Annotated[SupplierSearching, Depends(searching)],
    registry: Annotated[Metrics, Depends(metrics)],
) -> SearchResponseDto:
    log_search_request(payload.text)
    query = to_query(payload, locale)
    result = await service.search(query)
    report_search(registry, result)
    response.headers["Location"] = f"/api/searches/{result.search_id}"
    return to_response(result)


@router.get("", responses=ERRORS)
async def recent_searches(
    service: Annotated[SupplierSearching, Depends(searching)],
    limit: Annotated[int, Query(ge=1, le=RECENT_MAX)] = RECENT_DEFAULT,
) -> RecentSearchesDto:
    summaries = await service.recent(limit)
    return RecentSearchesDto(searches=[to_summary(summary) for summary in summaries])


@router.get("/{search_id}", responses=ERRORS)
async def get_search(
    search_id: str,
    service: Annotated[SupplierSearching, Depends(searching)],
) -> SearchResponseDto:
    return to_response(await service.get(parse_search_id(search_id)))
