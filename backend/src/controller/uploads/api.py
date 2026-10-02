import logging
import re
from dataclasses import asdict
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from src.controller.uploads.csv_file import NoticeReader
from src.controller.uploads.item_file import read_positions
from src.controller.uploads.presentation import detail, result, summary
from src.controller.uploads.protocols import UploadManager
from src.controller.uploads.received import receive_file
from src.models.errors import DomainError
from src.service.errors import (
    LotNotFoundError,
    SearchUnavailableError,
    StorageUnavailableError,
    UploadError,
    UploadNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/uploads")
reader = NoticeReader()
ENGINE = ("supplier_search",)


class SelectedLots(BaseModel):
    lotIds: list[str] = Field(min_length=1, max_length=20)


def owner(request: Request, response: Response) -> str:
    value = request.cookies.get("rlt_session", "")
    if not re.fullmatch(r"[a-f0-9]{32}", value):
        value = uuid4().hex
        response.set_cookie(
            "rlt_session",
            value,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
            max_age=604800,
        )
    return value


async def get_upload(request: Request, response: Response, upload_id: str):
    manager: UploadManager = request.app.state.uploads
    upload = await manager.get(owner(request, response), upload_id)
    if upload is None:
        raise UploadNotFoundError(upload_id)
    return upload


@router.get("")
async def list_uploads(request: Request, response: Response):
    manager: UploadManager = request.app.state.uploads
    uploads = await manager.list(owner(request, response))
    return {"uploads": [summary(upload) for upload in uploads]}


@router.post("")
async def create_upload(request: Request, response: Response):
    received = await receive_file(request)
    notices = await reader.read(received.content)
    if received.positions is not None:
        notices = await read_positions(notices, received.positions)
    manager: UploadManager = request.app.state.uploads
    try:
        filename = received.name
        if received.positions_name:
            filename += " + " + received.positions_name
        upload = await manager.create(owner(request, response), filename, notices)
    except (DomainError, UploadError, StorageUnavailableError):
        raise
    except Exception as error:
        logger.warning("upload creation failed", exc_info=error)
        raise SearchUnavailableError(ENGINE) from error
    return summary(upload)


@router.get("/{upload_id}")
async def get_detail(upload_id: str, request: Request, response: Response):
    return detail(await get_upload(request, response, upload_id))


@router.get("/{upload_id}/summary")
async def get_summary(upload_id: str, request: Request, response: Response):
    return summary(await get_upload(request, response, upload_id))


@router.get("/{upload_id}/lots/{lot_id}")
async def get_lot(upload_id: str, lot_id: str, request: Request, response: Response):
    upload = await get_upload(request, response, upload_id)
    for lot in upload.lots:
        if lot.notice.lot_id == lot_id:
            return {**result(upload, lot), "upload": summary(upload)}
    raise LotNotFoundError(upload_id, lot_id)


@router.post("/{upload_id}/results")
async def get_results(upload_id: str, body: SelectedLots, request: Request, response: Response):
    upload = await get_upload(request, response, upload_id)
    selected = set(body.lotIds)
    return {
        "results": [result(upload, lot) for lot in upload.lots if lot.notice.lot_id in selected]
    }


@router.get("/{upload_id}/lots/{lot_id}/evidence/{inn}/{purchase_id}")
async def get_evidence(
    upload_id: str,
    lot_id: str,
    inn: str,
    purchase_id: str,
    request: Request,
    response: Response,
):
    upload = await get_upload(request, response, upload_id)
    for lot in upload.lots:
        if lot.notice.lot_id != lot_id:
            continue
        for candidate in lot.candidates:
            if candidate.inn != inn:
                continue
            for purchase in candidate.purchases:
                if purchase.lot_id == purchase_id:
                    return {
                        "supplier_inn": inn,
                        "category": candidate.category,
                        "provenance": "procurement_archive",
                        **asdict(purchase),
                    }
    raise HTTPException(404)
