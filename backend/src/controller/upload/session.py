import re
from uuid import uuid4

from fastapi import Request, Response

SESSION_COOKIE = "rlt_session"
SESSION_PATTERN = re.compile(r"[0-9a-f]{32}")
SESSION_MAX_AGE = 30 * 24 * 3600


def session_owner(request: Request, response: Response) -> str:
    value = request.cookies.get(SESSION_COOKIE, "")
    if SESSION_PATTERN.fullmatch(value):
        return value
    value = uuid4().hex
    response.set_cookie(
        SESSION_COOKIE,
        value,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/api",
    )
    return value
