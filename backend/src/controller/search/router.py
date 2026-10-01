import hashlib
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from src.controller.http.errors import ApiErrorDto
from src.controller.http.locale import request_locale
from src.controller.http.middleware import request_id_of
from src.controller.http.state import Services, services
from src.controller.search.dto import RecentSearchesDto, SearchRequestDto, SearchResponseDto
from src.controller.search.mapper import parse_search_id, to_query, to_response, to_summary
from src.controller.search.protocols import SupplierSearching
from src.models.enums import Locale

RECENT_DEFAULT = 10
RECENT_MAX = 50

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/searches", tags=["searches"])

ERRORS: dict[int | str, dict[str, object]] = {
    code: {"model": ApiErrorDto} for code in (404, 422, 500, 503, 504)
}


async def searching(found: Annotated[Services, Depends(services)]) -> SupplierSearching:
    return found.supplier_search


def log_search(request: Request, text: str) -> None:
    logger.info(
        "search requested",
        extra={
            "request_id": request_id_of(request),
            "text_length": len(text),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
    )


@router.post("", status_code=status.HTTP_201_CREATED, responses=ERRORS)
async def create_search(
    payload: SearchRequestDto,
    request: Request,
    response: Response,
    locale: Annotated[Locale, Depends(request_locale)],
    service: Annotated[SupplierSearching, Depends(searching)],
) -> SearchResponseDto:
    log_search(request, payload.text)
    query = to_query(payload, locale)
    result = await service.search(query)
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
