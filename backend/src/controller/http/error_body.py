from http import HTTPStatus

from src.controller.http.schema import CamelModel

INTERNAL_STATUS = HTTPStatus.INTERNAL_SERVER_ERROR
INTERNAL_CODE = "internal_error"
INTERNAL_MESSAGE = "internal error"


class ApiErrorDto(CamelModel):
    code: str
    message: str
    request_id: str


def error_body(code: str, message: str, request_id: str) -> dict[str, str]:
    dto = ApiErrorDto(code=code, message=message, request_id=request_id)
    return dto.model_dump(by_alias=True, mode="json")


def internal_body(request_id: str) -> dict[str, str]:
    return error_body(INTERNAL_CODE, INTERNAL_MESSAGE, request_id)
