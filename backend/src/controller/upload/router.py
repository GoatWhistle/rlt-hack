import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from src.controller.http.error_body import ApiErrorDto
from src.controller.http.middleware import request_id_of
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

RECENT_DEFAULT = 20
RECENT_MAX = 50

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ERRORS: dict[int | str, dict[str, object]] = {
    code: {"model": ApiErrorDto} for code in (400, 404, 413, 415, 422, 429, 500, 503)
}


async def uploading(found: Annotated[Services, Depends(services)]) -> ProcurementUploads:
    return found.procurement_uploads


@router.get("", responses=ERRORS)
async def recent_uploads(
    service: Annotated[ProcurementUploads, Depends(uploading)],
    limit: Annotated[int, Query(ge=1, le=RECENT_MAX)] = RECENT_DEFAULT,
) -> UploadListDto:
    return UploadListDto(uploads=[summary_dto(item) for item in await service.recent(limit)])


@router.post("", status_code=status.HTTP_201_CREATED, responses=ERRORS)
async def create_upload(
    request: Request,
    response: Response,
    settings: Annotated[ApiSettings, Depends(api_settings)],
    service: Annotated[ProcurementUploads, Depends(uploading)],
) -> UploadSummaryDto:
    received = await receive_file(request, settings.upload_max_bytes)
    logger.info(
        "upload received",
        extra={"request_id": request_id_of(request), "bytes": len(received.content)},
    )
    summary = await service.upload(received.name, received.content)
    response.headers["Location"] = f"/api/uploads/{summary.upload.upload_id}"
    return summary_dto(summary)


@router.get("/{upload_id}", responses=ERRORS)
async def get_upload(
    upload_id: str,
    service: Annotated[ProcurementUploads, Depends(uploading)],
) -> UploadDetailDto:
    return detail_dto(await service.get(parse_upload_id(upload_id)))


@router.get("/{upload_id}/lots/{lot_id}", responses=ERRORS)
async def get_lot(
    upload_id: str,
    lot_id: str,
    service: Annotated[ProcurementUploads, Depends(uploading)],
) -> LotDetailDto:
    upload = parse_upload_id(upload_id)
    return lot_detail_dto(await service.lot(upload, parse_lot_id(upload, lot_id)))


@router.post("/{upload_id}/results", responses=ERRORS)
async def lot_results(
    upload_id: str,
    payload: ResultsRequestDto,
    service: Annotated[ProcurementUploads, Depends(uploading)],
) -> LotResultsDto:
    return results_dto(await service.results(parse_upload_id(upload_id), payload.lot_ids))
