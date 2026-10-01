from http import HTTPStatus
from typing import Annotated

from fastapi import Path
from fastapi.routing import APIRoute

from src.controller.http.error_body import ApiErrorDto

type Responses = dict[int | str, dict[str, object]]

UuidPath = Annotated[str, Path(json_schema_extra={"format": "uuid"})]
LOCATION = {
    "Location": {"description": "Address of the created resource", "schema": {"type": "string"}}
}
RETRY_AFTER = {"Retry-After": {"description": "Seconds to wait", "schema": {"type": "integer"}}}
RETRYABLE = frozenset(
    {HTTPStatus.TOO_MANY_REQUESTS, HTTPStatus.SERVICE_UNAVAILABLE, HTTPStatus.GATEWAY_TIMEOUT}
)


def operation_id(route: APIRoute) -> str:
    return route.name


def errors(*statuses: HTTPStatus) -> Responses:
    found: Responses = {}
    implied = (HTTPStatus.UNPROCESSABLE_ENTITY, HTTPStatus.INTERNAL_SERVER_ERROR)
    for status in sorted({*statuses, *implied}):
        entry: dict[str, object] = {"model": ApiErrorDto, "description": status.phrase}
        if status in RETRYABLE:
            entry["headers"] = RETRY_AFTER
        found[int(status)] = entry
    return found


def created(*statuses: HTTPStatus) -> Responses:
    return {
        int(HTTPStatus.CREATED): {"description": HTTPStatus.CREATED.phrase, "headers": LOCATION},
        **errors(*statuses),
    }


def not_modified(*statuses: HTTPStatus) -> Responses:
    return {
        int(HTTPStatus.NOT_MODIFIED): {"description": "The cached copy is still current"},
        **errors(*statuses),
    }


MULTIPART_FILE = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["file"],
                    "properties": {"file": {"type": "string", "format": "binary"}},
                }
            }
        },
    }
}
