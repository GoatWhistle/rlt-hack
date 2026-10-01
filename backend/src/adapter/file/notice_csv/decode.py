from src.models.errors import UnreadableNoticeFileError, UnsupportedNoticeFormatError

BINARY_SIGNATURES = (b"PK\x03\x04", b"\xd0\xcf\x11\xe0", b"%PDF")
SNIFF_BYTES = 4096
FALLBACK_ENCODING = "cp1251"
BOM = "﻿"


def decode_notices(content: bytes) -> str:
    if content.startswith(BINARY_SIGNATURES) or b"\x00" in content[:SNIFF_BYTES]:
        raise UnsupportedNoticeFormatError
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = _legacy(content)
    return text.removeprefix(BOM)


def _legacy(content: bytes) -> str:
    try:
        return content.decode(FALLBACK_ENCODING)
    except UnicodeDecodeError as error:
        raise UnreadableNoticeFileError("unknown text encoding") from error
