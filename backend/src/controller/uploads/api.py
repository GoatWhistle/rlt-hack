import asyncio
import re
from dataclasses import asdict
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field

from src.controller.uploads.csv_file import decode_notices
from src.controller.uploads.presentation import detail, result, summary
from src.controller.uploads.protocols import UploadManager
from src.service.errors import ServiceError

router = APIRouter(prefix="/api/uploads")


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
        raise HTTPException(404)
    return upload


@router.get("")
async def list_uploads(request: Request, response: Response):
    manager: UploadManager = request.app.state.uploads
    uploads = await manager.list(owner(request, response))
    return {"uploads": [summary(upload) for upload in uploads]}


@router.post("")
async def create_upload(file: UploadFile, request: Request, response: Response):
    data = await file.read(2 * 1024 * 1024 + 1)
    await file.close()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(413)
    try:
        notices = await asyncio.to_thread(decode_notices, data)
    except (ValueError, UnicodeError):
        raise HTTPException(422, "CSV: 1–20 строк, lot_id и procedure_name") from None
    manager: UploadManager = request.app.state.uploads
    try:
        upload = await manager.create(
            owner(request, response), (file.filename or "upload.csv")[:200], notices
        )
    except ServiceError:
        raise HTTPException(422) from None
    except Exception:
        raise HTTPException(503, "search_unavailable") from None
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
    raise HTTPException(404)


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
