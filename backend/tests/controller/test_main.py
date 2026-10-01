from typing import Any

import pytest
import uvicorn
from fastapi import FastAPI

from src.controller.api import main


def test_build_app_reads_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    levels: list[str] = []
    monkeypatch.setattr(main, "configure_logging", levels.append)
    monkeypatch.setenv("API_DOCS", "false")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    app = main.build_app()
    assert isinstance(app, FastAPI)
    assert app.docs_url is None
    assert app.title == main.API_TITLE
    assert levels == ["DEBUG"]


def test_run_starts_uvicorn_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "9001")
    main.run()
    [(args, kwargs)] = calls
    assert args == ("src.controller.api.main:build_app",)
    assert kwargs["factory"] is True
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 9001
