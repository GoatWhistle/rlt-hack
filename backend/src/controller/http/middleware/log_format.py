import json
import logging
from datetime import UTC, datetime

from src.controller.http.middleware.correlation import RequestIdFilter

RESERVED = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {
    "message",
    "asctime",
    "taskName",
}
NOISY_LOGGERS = ("urllib3", "clickhouse_connect")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update((key, value) for key, value in vars(record).items() if key not in RESERVED)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def json_handler() -> logging.Handler:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    return handler


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.ERROR)
    if any(isinstance(handler.formatter, JsonFormatter) for handler in root.handlers):
        return
    root.addHandler(json_handler())
