from typing import Annotated

from fastapi import APIRouter, Depends

from src.controller.http.error_body import ApiErrorDto
from src.controller.http.state import Services, services
from src.controller.supplier.dto import SupplierProfileDto
from src.controller.supplier.mapper import parse_supplier_id, to_profile
from src.controller.supplier.protocols import SupplierProfiles

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])

ERRORS: dict[int | str, dict[str, object]] = {
    code: {"model": ApiErrorDto} for code in (404, 500, 503)
}


async def profiles(found: Annotated[Services, Depends(services)]) -> SupplierProfiles:
    return found.supplier_profiles


@router.get("/{supplier_id}", responses=ERRORS)
async def get_supplier(
    supplier_id: str,
    service: Annotated[SupplierProfiles, Depends(profiles)],
) -> SupplierProfileDto:
    return to_profile(await service.get(parse_supplier_id(supplier_id)))
