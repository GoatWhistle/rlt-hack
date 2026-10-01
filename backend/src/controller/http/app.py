from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI

from src.controller.health.router import router as health_router
from src.controller.http.errors import install_error_handlers
from src.controller.http.metrics import Metrics
from src.controller.http.middleware import RequestContextMiddleware
from src.controller.http.protocols import ServiceProvider
from src.controller.http.settings import ApiSettings
from src.controller.http.state import Services
from src.controller.metrics.router import router as metrics_router
from src.controller.search.router import router as search_router
from src.controller.supplier.router import router as supplier_router
from src.controller.upload.router import router as upload_router

DOCS_URL = "/api/docs"
OPENAPI_URL = "/api/openapi.json"

Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def lifespan_for(provider: ServiceProvider) -> Lifespan:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            resolved = await Services.resolve(provider)
            app.state.services = resolved
            await resolved.procurement_uploads.start()
            try:
                yield
            finally:
                await resolved.procurement_uploads.stop()
        finally:
            await provider.aclose()

    return lifespan


def create_app(provider: ServiceProvider, settings: ApiSettings) -> FastAPI:
    app = FastAPI(
        title=settings.title,
        version=settings.version,
        lifespan=lifespan_for(provider),
        docs_url=DOCS_URL if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url=OPENAPI_URL if settings.docs_enabled else None,
    )
    app.state.settings = settings
    app.state.metrics = Metrics()
    install_error_handlers(app)
    app.add_middleware(RequestContextMiddleware, metrics=app.state.metrics)
    routers = (search_router, supplier_router, upload_router, health_router, metrics_router)
    for router in routers:
        app.include_router(router)
    return app
