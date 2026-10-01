from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from src.controller.http.caching import entity_tag, fresh, not_modified, revalidated, uncached
from src.controller.http.locale import request_locale
from src.controller.http.metrics import Metrics
from src.controller.http.openapi import UuidPath, created, errors
from src.controller.http.openapi import not_modified as conditional
from src.controller.http.state import Services, metrics, services
from src.controller.search.dto import RecentSearchesDto, SearchRequestDto, SearchResponseDto
from src.controller.search.mapper import parse_search_id, to_query, to_response, to_summary
from src.controller.search.observe import log_search_request, report_search
from src.controller.search.protocols import SupplierSearching
from src.models.enums import Locale, WarningCode

RECENT_DEFAULT = 10
RECENT_MAX = 50
VIEW_VERSION = 1

router = APIRouter(prefix="/api/searches", tags=["searches"])


async def searching(found: Annotated[Services, Depends(services)]) -> SupplierSearching:
    return found.supplier_search


def search_tag(search_id: str) -> str:
    return entity_tag((search_id, VIEW_VERSION))


@router.post(
    "",
    status_code=HTTPStatus.CREATED,
    responses=created(
        HTTPStatus.UNPROCESSABLE_ENTITY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        HTTPStatus.GATEWAY_TIMEOUT,
    ),
)
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
    if any(warning.code == WarningCode.ARCHIVE_FAILED for warning in result.warnings):
        response.status_code = HTTPStatus.OK
    else:
        response.headers["Location"] = f"/api/searches/{result.search_id}"
    return to_response(result)


@router.get("", responses=errors(HTTPStatus.SERVICE_UNAVAILABLE))
async def recent_searches(
    response: Response,
    service: Annotated[SupplierSearching, Depends(searching)],
    limit: Annotated[int, Query(ge=1, le=RECENT_MAX)] = RECENT_DEFAULT,
) -> RecentSearchesDto:
    uncached(response)
    summaries = await service.recent(limit)
    return RecentSearchesDto(searches=[to_summary(summary) for summary in summaries])


@router.get(
    "/{search_id}",
    response_model=SearchResponseDto,
    responses=conditional(HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE),
)
async def get_search(
    search_id: UuidPath,
    request: Request,
    response: Response,
    service: Annotated[SupplierSearching, Depends(searching)],
) -> Response | SearchResponseDto:
    parsed = parse_search_id(search_id)
    tag = search_tag(str(parsed))
    if fresh(request, tag):
        return not_modified(tag)
    result = await service.get(parsed)
    revalidated(response, tag)
    return to_response(result)
