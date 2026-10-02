import logging
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from src.application.supplier_search import supplier_search
from src.application.uploads import upload_service
from src.controller.http.errors import install_error_handlers
from src.controller.http.middleware import RequestContextMiddleware
from src.controller.search.protocols import SearchEngine
from src.controller.uploads.api import ENGINE, router
from src.models.errors import EmptySearchTextError
from src.service.errors import SearchUnavailableError, StorageUnavailableError

logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=10, ge=1, le=100)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with supplier_search() as engine:
        app.state.search = engine
        app.state.uploads = upload_service(engine)
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
install_error_handlers(app)
app.add_middleware(RequestContextMiddleware)
app.include_router(router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/suppliers/search")
async def search(body: SearchRequest, request: Request):
    if not body.query.strip():
        raise EmptySearchTextError
    engine: SearchEngine = request.app.state.search
    try:
        results = await engine.search(body.query, body.limit)
    except StorageUnavailableError:
        raise
    except Exception as error:
        logger.warning("supplier search failed", exc_info=error)
        raise SearchUnavailableError(ENGINE) from error
    return {"query": body.query, "suppliers": [asdict(item) for item in results]}
