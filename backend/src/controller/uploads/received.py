from dataclasses import dataclass

from fastapi import Request
from starlette.datastructures import UploadFile

from src.controller.errors import FileTooLargeError, MissingFileError

FILE_FIELD = "file"
MAX_BYTES = 2 * 1024 * 1024
MULTIPART_OVERHEAD = 64 * 1024
MAX_FORM_FIELDS = 8
MAX_NAME_CHARS = 200
DEFAULT_NAME = "upload.csv"


@dataclass(frozen=True, slots=True)
class ReceivedFile:
    name: str
    content: bytes


def declared_length(request: Request) -> int | None:
    raw = request.headers.get("content-length", "")
    return int(raw) if raw.isdigit() else None


async def receive_file(request: Request, limit: int = MAX_BYTES) -> ReceivedFile:
    declared = declared_length(request)
    if declared is not None and declared > limit + MULTIPART_OVERHEAD:
        raise FileTooLargeError(limit)
    async with request.form(max_files=1, max_fields=MAX_FORM_FIELDS) as form:
        file = form.get(FILE_FIELD)
        if not isinstance(file, UploadFile):
            raise MissingFileError
        name = (file.filename or DEFAULT_NAME)[:MAX_NAME_CHARS]
        content = await file.read(limit + 1)
    if len(content) > limit:
        raise FileTooLargeError(limit)
    return ReceivedFile(name, content)
