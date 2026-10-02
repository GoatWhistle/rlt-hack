from typing import Any

import pytest
from fastapi import FastAPI

ERROR_SCHEMA = "#/components/schemas/ApiErrorDto"


@pytest.fixture
def schema(app: FastAPI) -> dict[str, Any]:
    return app.openapi()


def operations(schema: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    return [
        (path, method, operation)
        for path, item in schema["paths"].items()
        for method, operation in item.items()
    ]


def test_every_error_response_uses_the_api_error_body(schema: dict[str, Any]) -> None:
    for path, method, operation in operations(schema):
        for status, response in operation["responses"].items():
            if int(status) < 400 or path == "/api/health/ready":
                continue
            content = response["content"]["application/json"]["schema"]
            assert content == {"$ref": ERROR_SCHEMA}, (path, method, status)


def test_names_are_short_and_stable(schema: dict[str, Any]) -> None:
    names = schema["components"]["schemas"]
    assert not [name for name in names if "__" in name]
    identifiers = [operation["operationId"] for _, _, operation in operations(schema)]
    assert len(identifiers) == len(set(identifiers))
    assert "create_search" in identifiers


def test_times_and_identifiers_have_formats(schema: dict[str, Any]) -> None:
    created = schema["components"]["schemas"]["SearchResponseDto"]["properties"]["createdAt"]
    assert (created["type"], created["format"]) == ("string", "date-time")
    parameters = schema["paths"]["/api/searches/{search_id}"]["get"]["parameters"]
    assert parameters[0]["schema"]["format"] == "uuid"
    location = schema["paths"]["/api/searches"]["post"]["responses"]["201"]["headers"]
    assert "Location" in location
    retry = schema["paths"]["/api/searches"]["post"]["responses"]["503"]["headers"]
    assert "Retry-After" in retry
