from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.application.supplier_search import supplier_search
from src.controller.search.protocols import SearchEngine
from src.controller.search.recommendations import (
    MAX_LIMIT,
    SCHEMA_VERSION,
    RecommendationRequest,
    to_response,
)
from src.service.errors import ServiceError


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=10, ge=1, le=MAX_LIMIT)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with supplier_search() as engine:
        app.state.search = engine
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/recommendations", response_model=None)
async def recommendations(
    body: RecommendationRequest, request: Request
) -> dict[str, Any] | JSONResponse:
    if body.schema_version.partition(".")[0] != SCHEMA_VERSION.partition(".")[0]:
        return JSONResponse({"code": "unsupported_schema"}, status_code=422)
    engine: SearchEngine = request.app.state.search
    try:
        found = await engine.search(body.text, body.options.candidate_limit)
    except ServiceError:
        return JSONResponse({"code": "invalid_search"}, status_code=422)
    except Exception:
        return JSONResponse({"code": "search_unavailable"}, status_code=503)
    version = engine.version or "supplier-index"
    return to_response(body, found, version).model_dump(by_alias=True, mode="json")


@app.post("/api/suppliers/search", response_model=None)
async def search(body: SearchRequest, request: Request) -> dict[str, Any] | JSONResponse:
    engine: SearchEngine = request.app.state.search
    try:
        results = await engine.search(body.query, body.limit)
    except ServiceError:
        return JSONResponse({"code": "invalid_search"}, status_code=422)
    except Exception:
        return JSONResponse({"code": "search_unavailable"}, status_code=503)
    return {"query": body.query, "suppliers": [asdict(item) for item in results]}
