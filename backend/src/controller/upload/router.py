import logging
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from src.controller.http.caching import entity_tag, fresh, not_modified, revalidated, uncached
from src.controller.http.openapi import MULTIPART_FILE, UuidPath, created, errors
from src.controller.http.openapi import not_modified as conditional
from src.controller.http.settings import ApiSettings
from src.controller.http.state import Services, api_settings, services
from src.controller.upload.dto import (
    LotDetailDto,
    LotResultsDto,
    ResultsRequestDto,
    UploadDetailDto,
    UploadListDto,
    UploadSummaryDto,
)
from src.controller.upload.files import receive_file
from src.controller.upload.mapper import (
    detail_dto,
    lot_detail_dto,
    parse_lot_id,
    parse_upload_id,
    results_dto,
    summary_dto,
)
from src.controller.upload.protocols import ProcurementUploads
from src.models.upload import UploadSummary

RECENT_DEFAULT = 20
RECENT_MAX = 50
DETAIL_VERSION = 2

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


async def uploading(found: Annotated[Services, Depends(services)]) -> ProcurementUploads:
    return found.procurement_uploads


def progress_tag(summary: UploadSummary) -> str:
    counts = summary.counts
    return entity_tag(
        (
            summary.upload.upload_id,
            summary.processed,
            counts.ready,
            counts.needs_check,
            counts.no_candidates,
            counts.failed,
            DETAIL_VERSION,
        )
    )


@router.get(
    "",
    responses=errors(HTTPStatus.UNPROCESSABLE_ENTITY, HTTPStatus.SERVICE_UNAVAILABLE),
)
async def recent_uploads(
    response: Response,
    service: Annotated[ProcurementUploads, Depends(uploading)],
    limit: Annotated[int, Query(ge=1, le=RECENT_MAX)] = RECENT_DEFAULT,
) -> UploadListDto:
    uncached(response)
    return UploadListDto(uploads=[summary_dto(item) for item in await service.recent(limit)])


@router.post(
    "",
    status_code=HTTPStatus.CREATED,
    responses=created(
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.SERVICE_UNAVAILABLE,
    ),
    openapi_extra=MULTIPART_FILE,
)
async def create_upload(
    request: Request,
    response: Response,
    settings: Annotated[ApiSettings, Depends(api_settings)],
    service: Annotated[ProcurementUploads, Depends(uploading)],
) -> UploadSummaryDto:
    received = await receive_file(request, settings.upload_max_bytes)
    logger.info("upload received", extra={"bytes": len(received.content)})
    summary = await service.upload(received.name, received.content)
    response.headers["Location"] = f"/api/uploads/{summary.upload.upload_id}"
    return summary_dto(summary)


@router.get(
    "/{upload_id}/summary",
    response_model=UploadSummaryDto,
    responses=conditional(HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE),
)
async def get_upload_summary(
    upload_id: UuidPath,
    request: Request,
    response: Response,
    service: Annotated[ProcurementUploads, Depends(uploading)],
) -> Response | UploadSummaryDto:
    summary = await service.summary(parse_upload_id(upload_id))
    tag = progress_tag(summary)
    if fresh(request, tag):
        return not_modified(tag)
    revalidated(response, tag)
    return summary_dto(summary)


@router.get(
    "/{upload_id}",
    response_model=UploadDetailDto,
    responses=conditional(HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE),
)
async def get_upload(
    upload_id: UuidPath,
    request: Request,
    response: Response,
    service: Annotated[ProcurementUploads, Depends(uploading)],
) -> Response | UploadDetailDto:
    parsed = parse_upload_id(upload_id)
    if request.headers.get("if-none-match"):
        tag = progress_tag(await service.summary(parsed))
        if fresh(request, tag):
            return not_modified(tag)
    detail = await service.get(parsed)
    revalidated(response, progress_tag(detail.summary))
    return detail_dto(detail)


@router.get(
    "/{upload_id}/lots/{lot_id}",
    responses=errors(HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE),
)
async def get_lot(
    upload_id: UuidPath,
    lot_id: str,
    service: Annotated[ProcurementUploads, Depends(uploading)],
) -> LotDetailDto:
    upload = parse_upload_id(upload_id)
    return lot_detail_dto(await service.lot(upload, parse_lot_id(upload, lot_id)))


@router.post(
    "/{upload_id}/results",
    responses=errors(
        HTTPStatus.NOT_FOUND, HTTPStatus.UNPROCESSABLE_ENTITY, HTTPStatus.SERVICE_UNAVAILABLE
    ),
)
async def lot_results(
    upload_id: UuidPath,
    payload: ResultsRequestDto,
    service: Annotated[ProcurementUploads, Depends(uploading)],
) -> LotResultsDto:
    return results_dto(await service.results(parse_upload_id(upload_id), payload.lot_ids))
