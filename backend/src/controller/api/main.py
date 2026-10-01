import uvicorn
from fastapi import FastAPI

from src.application.api import ApiContainer
from src.application.config import AppConfig
from src.application.container import Container
from src.controller.http.app import create_app
from src.controller.http.correlation import current_request_id
from src.controller.http.log_format import configure_logging
from src.controller.http.settings import ApiSettings

APP_FACTORY = "src.controller.api.main:build_app"
API_TITLE = "LOTIVE API"
API_VERSION = "0.1.0"


def build_app() -> FastAPI:
    config = AppConfig.from_env()
    configure_logging(config.log_level)
    settings = ApiSettings(
        title=API_TITLE,
        version=API_VERSION,
        docs_enabled=config.api.docs_enabled,
        upload_max_bytes=config.upload.max_bytes,
    )
    container = Container(config, current_request_id)
    api = ApiContainer(
        config,
        container.api_gateway,
        container.aclose,
        background=container.background_gateway,
        control=container.control_gateway,
        correlation=current_request_id,
    )
    return create_app(api, settings)


def run() -> None:
    config = AppConfig.from_env()
    configure_logging(config.log_level)
    uvicorn.run(
        APP_FACTORY,
        factory=True,
        host=config.api.host,
        port=config.api.port,
        log_config=None,
        access_log=False,
        proxy_headers=True,
    )
