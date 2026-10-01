from dataclasses import dataclass

from fastapi import Request
from starlette.datastructures import UploadFile

from src.controller.errors import FileTooLargeError, MissingFileError, UnsupportedFileTypeError

FILE_FIELD = "file"
ALLOWED_EXTENSIONS = (".csv",)
MULTIPART_OVERHEAD = 64 * 1024
MAX_FORM_FIELDS = 8


@dataclass(frozen=True, slots=True)
class ReceivedFile:
    name: str
    content: bytes


def _declared_length(request: Request) -> int | None:
    raw = request.headers.get("content-length", "")
    return int(raw) if raw.isdigit() else None


async def receive_file(request: Request, limit: int) -> ReceivedFile:
    declared = _declared_length(request)
    if declared is not None and declared > limit + MULTIPART_OVERHEAD:
        raise FileTooLargeError(limit)
    async with request.form(max_files=1, max_fields=MAX_FORM_FIELDS) as form:
        file = form.get(FILE_FIELD)
        if not isinstance(file, UploadFile):
            raise MissingFileError
        name = file.filename or ""
        if not name.lower().endswith(ALLOWED_EXTENSIONS):
            raise UnsupportedFileTypeError(ALLOWED_EXTENSIONS)
        content = await file.read(limit + 1)
    if len(content) > limit:
        raise FileTooLargeError(limit)
    return ReceivedFile(name=name, content=content)
