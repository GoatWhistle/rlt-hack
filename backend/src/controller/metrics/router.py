from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from src.controller.http.middleware.metrics import Metrics
from src.controller.http.state import metrics

PROMETHEUS_TEXT = "text/plain; version=0.0.4; charset=utf-8"

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("", include_in_schema=False)
async def exposition(registry: Annotated[Metrics, Depends(metrics)]) -> PlainTextResponse:
    return PlainTextResponse(registry.render(), media_type=PROMETHEUS_TEXT)
