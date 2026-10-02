import logging
from contextvars import ContextVar, Token

REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    return REQUEST_ID.get()


def bind_request_id(request_id: str) -> Token[str | None]:
    return REQUEST_ID.set(request_id)


def release_request_id(token: Token[str | None]) -> None:
    REQUEST_ID.reset(token)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = REQUEST_ID.get()
        if request_id is not None and not getattr(record, "request_id", None):
            record.request_id = request_id
        return True
