import json
import logging
import sys
from collections.abc import Iterator

import pytest

from src.controller.http.log_format import JsonFormatter, configure_logging


@pytest.fixture
def root_logger() -> Iterator[logging.Logger]:
    root = logging.getLogger()
    handlers = list(root.handlers)
    level = root.level
    yield root
    root.handlers = handlers
    root.setLevel(level)


def make_record(exc_info: bool = False) -> logging.LogRecord:
    error = None
    if exc_info:
        try:
            raise ValueError("boom")
        except ValueError:
            error = sys.exc_info()
    record = logging.LogRecord("api", logging.INFO, __file__, 1, "done %s", ("now",), error)
    record.text_length = 12
    return record


def test_formatter_writes_json_with_extras() -> None:
    payload = json.loads(JsonFormatter().format(make_record()))
    assert payload["message"] == "done now"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "api"
    assert payload["text_length"] == 12
    assert "exception" not in payload
    assert "args" not in payload


def test_formatter_includes_exception() -> None:
    payload = json.loads(JsonFormatter().format(make_record(exc_info=True)))
    assert "ValueError: boom" in payload["exception"]


def test_configure_logging_is_idempotent(root_logger: logging.Logger) -> None:
    configure_logging("warning")
    configure_logging("info")
    json_handlers = [
        handler for handler in root_logger.handlers if isinstance(handler.formatter, JsonFormatter)
    ]
    assert len(json_handlers) == 1
    assert root_logger.level == logging.INFO
