from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from src.controller.health.dto import LiveDto, ReadinessDto
from src.controller.health.protocols import ReadinessChecking
from src.controller.http.state import Services, services

router = APIRouter(prefix="/api/health", tags=["health"])


async def checking(found: Annotated[Services, Depends(services)]) -> ReadinessChecking:
    return found.health


@router.get("/live")
async def live() -> LiveDto:
    return LiveDto()


@router.get("/ready", responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessDto}})
async def ready(
    response: Response,
    checker: Annotated[ReadinessChecking, Depends(checking)],
) -> ReadinessDto:
    readiness = await checker.readiness()
    if not readiness.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessDto.of(readiness)
