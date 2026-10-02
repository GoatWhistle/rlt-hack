from dataclasses import dataclass
from typing import cast

from fastapi import Request

from src.controller.health.protocols import ReadinessChecking
from src.controller.http.metrics import Metrics
from src.controller.http.protocols import BackgroundTask, ServiceProvider
from src.controller.http.settings import ApiSettings
from src.controller.search.protocols import SupplierSearching
from src.controller.supplier.protocols import SupplierProfiles


@dataclass(frozen=True, slots=True)
class Services:
    supplier_search: SupplierSearching
    supplier_profiles: SupplierProfiles
    health: ReadinessChecking
    background: tuple[BackgroundTask, ...] = ()

    @classmethod
    async def resolve(cls, provider: ServiceProvider) -> "Services":
        return cls(
            supplier_search=await provider.supplier_search(),
            supplier_profiles=await provider.supplier_profiles(),
            health=await provider.health(),
            background=await provider.background(),
        )


async def services(request: Request) -> Services:
    return cast(Services, request.app.state.services)


async def api_settings(request: Request) -> ApiSettings:
    return cast(ApiSettings, request.app.state.settings)


async def metrics(request: Request) -> Metrics:
    return cast(Metrics, request.app.state.metrics)
