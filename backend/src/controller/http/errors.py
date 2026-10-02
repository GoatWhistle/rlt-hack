import logging
from dataclasses import dataclass
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from src.controller.errors import (
    FileTooLargeError,
    MissingFileError,
    RequestFileError,
    UnsupportedFileTypeError,
)
from src.controller.http.error_body import (
    INTERNAL_CODE,
    INTERNAL_MESSAGE,
    INTERNAL_STATUS,
    error_body,
)
from src.controller.http.middleware import REQUEST_ID_HEADER, request_id_of
from src.models.errors import (
    DomainError,
    EmptySearchTextError,
    InvalidCandidateLimitError,
    InvalidInputError,
    MissingNoticeColumnsError,
    NoValidLotsError,
    SearchTextTooLongError,
    TooManyNoticeRowsError,
    UnreadableNoticeFileError,
    UnsupportedNoticeFormatError,
)
from src.service.errors import (
    LotNotFoundError,
    PurchaseNotFoundError,
    SearchNotFoundError,
    SearchTimeoutError,
    SearchUnavailableError,
    ServiceError,
    StorageUnavailableError,
    SupplierNotFoundError,
    UninterpretableQueryError,
    UploadNotFoundError,
    UploadQueueFullError,
)

logger = logging.getLogger(__name__)

VALIDATION_MESSAGE = "request does not match the schema"
VALIDATION_DETAILS = 3


@dataclass(frozen=True, slots=True)
class ErrorKind:
    status: int
    code: str
    retry_after: int | None = None

    def headers(self) -> dict[str, str]:
        return {} if self.retry_after is None else {"Retry-After": str(self.retry_after)}


RETRY_AFTER_SECONDS = 5
QUEUE_RETRY_AFTER_SECONDS = 60

INTERNAL = ErrorKind(INTERNAL_STATUS, INTERNAL_CODE)
INVALID_REQUEST = ErrorKind(HTTPStatus.UNPROCESSABLE_ENTITY, "invalid_request")
UNSUPPORTED_FILE = ErrorKind(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "unsupported_file_type")

UPLOAD_ERRORS: tuple[tuple[type[Exception], ErrorKind], ...] = (
    (MissingFileError, ErrorKind(HTTPStatus.BAD_REQUEST, "missing_file")),
    (FileTooLargeError, ErrorKind(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "file_too_large")),
    (UnsupportedFileTypeError, UNSUPPORTED_FILE),
    (UnsupportedNoticeFormatError, UNSUPPORTED_FILE),
    (UnreadableNoticeFileError, ErrorKind(HTTPStatus.UNPROCESSABLE_ENTITY, "invalid_file")),
    (MissingNoticeColumnsError, ErrorKind(HTTPStatus.UNPROCESSABLE_ENTITY, "missing_columns")),
    (TooManyNoticeRowsError, ErrorKind(HTTPStatus.UNPROCESSABLE_ENTITY, "too_many_rows")),
    (NoValidLotsError, ErrorKind(HTTPStatus.UNPROCESSABLE_ENTITY, "no_valid_lots")),
    (UploadNotFoundError, ErrorKind(HTTPStatus.NOT_FOUND, "upload_not_found")),
    (
        UploadQueueFullError,
        ErrorKind(HTTPStatus.TOO_MANY_REQUESTS, "upload_queue_full", QUEUE_RETRY_AFTER_SECONDS),
    ),
    (LotNotFoundError, ErrorKind(HTTPStatus.NOT_FOUND, "lot_not_found")),
)

KNOWN_ERRORS: tuple[tuple[type[Exception], ErrorKind], ...] = (
    *UPLOAD_ERRORS,
    (EmptySearchTextError, ErrorKind(HTTPStatus.UNPROCESSABLE_ENTITY, "empty_query")),
    (SearchTextTooLongError, ErrorKind(HTTPStatus.UNPROCESSABLE_ENTITY, "query_too_long")),
    (InvalidCandidateLimitError, ErrorKind(HTTPStatus.UNPROCESSABLE_ENTITY, "invalid_limit")),
    (InvalidInputError, INVALID_REQUEST),
    (UninterpretableQueryError, ErrorKind(HTTPStatus.UNPROCESSABLE_ENTITY, "query_not_understood")),
    (SearchNotFoundError, ErrorKind(HTTPStatus.NOT_FOUND, "search_not_found")),
    (SupplierNotFoundError, ErrorKind(HTTPStatus.NOT_FOUND, "supplier_not_found")),
    (PurchaseNotFoundError, ErrorKind(HTTPStatus.NOT_FOUND, "purchase_not_found")),
    (
        SearchUnavailableError,
        ErrorKind(HTTPStatus.SERVICE_UNAVAILABLE, "search_unavailable", RETRY_AFTER_SECONDS),
    ),
    (
        StorageUnavailableError,
        ErrorKind(HTTPStatus.SERVICE_UNAVAILABLE, "storage_unavailable", RETRY_AFTER_SECONDS),
    ),
    (
        SearchTimeoutError,
        ErrorKind(HTTPStatus.GATEWAY_TIMEOUT, "search_timeout", RETRY_AFTER_SECONDS),
    ),
)

HTTP_CODES: dict[int, str] = {
    HTTPStatus.NOT_FOUND: "not_found",
    HTTPStatus.METHOD_NOT_ALLOWED: "method_not_allowed",
}


def classify(error: Exception) -> ErrorKind:
    return next((kind for known, kind in KNOWN_ERRORS if isinstance(error, known)), INTERNAL)


def error_response(
    request: Request,
    kind: ErrorKind,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = request_id_of(request)
    return JSONResponse(
        status_code=kind.status,
        content=error_body(kind.code, message, request_id),
        headers={**(headers or {}), REQUEST_ID_HEADER: request_id},
    )


def internal_error(request: Request, error: Exception) -> JSONResponse:
    logger.exception(
        "unhandled error",
        exc_info=error,
        extra={"request_id": request_id_of(request), "path": request.url.path},
    )
    return error_response(request, INTERNAL, INTERNAL_MESSAGE)


async def handle_known(request: Request, error: Exception) -> JSONResponse:
    kind = classify(error)
    if kind is INTERNAL:
        return internal_error(request, error)
    logger.info(
        "request rejected",
        extra={"request_id": request_id_of(request), "code": kind.code, "status": kind.status},
    )
    return error_response(request, kind, str(error), kind.headers())


async def handle_validation(request: Request, error: Exception) -> JSONResponse:
    details = error.errors() if isinstance(error, RequestValidationError) else ()
    described = [
        f"{'.'.join(str(part) for part in detail['loc'])}: {detail['msg']}"
        for detail in list(details)[:VALIDATION_DETAILS]
    ]
    message = "; ".join(described) or VALIDATION_MESSAGE
    return error_response(request, INVALID_REQUEST, message)


async def handle_http(request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, HTTPException):
        return internal_error(request, error)
    status = error.status_code
    fallback = INVALID_REQUEST.code if status < HTTPStatus.INTERNAL_SERVER_ERROR else INTERNAL.code
    kind = ErrorKind(status, HTTP_CODES.get(status, fallback))
    return error_response(request, kind, str(error.detail), dict(error.headers or {}))


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_known)
    app.add_exception_handler(ServiceError, handle_known)
    app.add_exception_handler(RequestFileError, handle_known)
    app.add_exception_handler(RequestValidationError, handle_validation)
    app.add_exception_handler(HTTPException, handle_http)
