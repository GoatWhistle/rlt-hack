from collections.abc import Iterable
from http import HTTPStatus

from fastapi import Request, Response

REVALIDATE = "private, no-cache"
NEVER_STORE = "no-store"
WEAK_PREFIX = "W/"


def entity_tag(parts: Iterable[object]) -> str:
    return WEAK_PREFIX + '"' + "-".join(str(part) for part in parts) + '"'


def fresh(request: Request, tag: str) -> bool:
    header = request.headers.get("if-none-match")
    if not header:
        return False
    offered = {value.strip().removeprefix(WEAK_PREFIX) for value in header.split(",")}
    return "*" in offered or tag.removeprefix(WEAK_PREFIX) in offered


def not_modified(tag: str) -> Response:
    return Response(
        status_code=HTTPStatus.NOT_MODIFIED,
        headers={"ETag": tag, "Cache-Control": REVALIDATE},
    )


def revalidated(response: Response, tag: str) -> None:
    response.headers["ETag"] = tag
    response.headers["Cache-Control"] = REVALIDATE


def uncached(response: Response) -> None:
    response.headers["Cache-Control"] = NEVER_STORE
