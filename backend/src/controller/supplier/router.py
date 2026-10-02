from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from src.controller.http.openapi import UuidPath, errors
from src.controller.http.state import Services, services
from src.controller.supplier.dto import ArchivePurchaseDto, SupplierProfileDto
from src.controller.supplier.mapper import parse_supplier_id, to_profile, to_purchase
from src.controller.supplier.protocols import SupplierProfiles

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


async def profiles(found: Annotated[Services, Depends(services)]) -> SupplierProfiles:
    return found.supplier_profiles


@router.get(
    "/{supplier_id}", responses=errors(HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE)
)
async def get_supplier(
    supplier_id: UuidPath,
    service: Annotated[SupplierProfiles, Depends(profiles)],
) -> SupplierProfileDto:
    return to_profile(await service.get(parse_supplier_id(supplier_id)))


@router.get(
    "/{supplier_id}/purchases/{lot_id}",
    responses=errors(HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE),
)
async def get_supplier_purchase(
    supplier_id: UuidPath,
    lot_id: Annotated[str, Path(max_length=128, pattern=r"^[0-9A-Za-z_.:-]+$")],
    service: Annotated[SupplierProfiles, Depends(profiles)],
) -> ArchivePurchaseDto:
    return to_purchase(await service.purchase(parse_supplier_id(supplier_id), lot_id))
