from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.application.supplier_search import supplier_search
from src.application.uploads import upload_service
from src.controller.search.protocols import SearchEngine
from src.controller.uploads.api import router
from src.service.errors import ServiceError


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
app.include_router(router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/suppliers/search")
async def search(body: SearchRequest, request: Request):
    engine: SearchEngine = request.app.state.search
    try:
        results = await engine.search(body.query, body.limit)
    except ServiceError:
        return JSONResponse({"code": "invalid_search"}, status_code=422)
    except Exception:
        return JSONResponse({"code": "search_unavailable"}, status_code=503)
    return {"query": body.query, "suppliers": [asdict(item) for item in results]}
