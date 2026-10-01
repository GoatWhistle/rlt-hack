from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from src.controller.http.app import create_app
from src.controller.http.settings import ApiSettings
from tests.fakes.http import FakeServiceProvider


@pytest.fixture
def provider() -> FakeServiceProvider:
    return FakeServiceProvider()


@pytest.fixture
def app(provider: FakeServiceProvider) -> FastAPI:
    return create_app(provider, ApiSettings())


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
