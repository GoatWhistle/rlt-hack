import asyncio
from collections import Counter, defaultdict
from dataclasses import replace
from hashlib import sha256

from src.controller.uploads.csv_file import MAX_COLUMNS, MAX_TEXT_CHARS, decode_text, records
from src.models.errors import (
    InvalidNoticeRowError,
    MissingNoticeColumnsError,
    UnreadableNoticeFileError,
)
from src.models.operations.upload import Notice, NoticePosition
from src.models.search.query_item import OKPD2_PATTERN

REQUIRED = ("lot_id", "product_name", "okpd2_code")


def attach_positions(notices: list[Notice], data: bytes) -> list[Notice]:
    rows = records(decode_text(data))
    header = next(rows, None)
    if header is None:
        raise UnreadableNoticeFileError("the item file is empty")
    names = [cell.strip().lower() for cell in header[1]]
    if len(names) > MAX_COLUMNS or len(set(names)) != len(names):
        raise UnreadableNoticeFileError("invalid item columns")
    missing = tuple(name for name in REQUIRED if name not in names)
    if missing:
        raise MissingNoticeColumnsError(missing)
    columns = [names.index(name) for name in REQUIRED]
    known = {notice.lot_id for notice in notices}
    grouped: dict[str, list[NoticePosition]] = defaultdict(list)
    repeats: Counter[str] = Counter()
    for line, cells in rows:
        if len(cells) != len(names):
            raise InvalidNoticeRowError(line, "item row does not match the header")
        lot_id, name, code = (" ".join(cells[index].split()) for index in columns)
        if lot_id not in known:
            raise InvalidNoticeRowError(line, "item lot_id has no matching notice")
        if not name or len(name) > MAX_TEXT_CHARS:
            raise InvalidNoticeRowError(line, "invalid product_name")
        if code and not OKPD2_PATTERN.fullmatch(code):
            raise InvalidNoticeRowError(line, "invalid okpd2_code")
        fingerprint = sha256(f"{lot_id}\0{name}\0{code}".encode()).hexdigest()[:24]
        grouped[lot_id].append(NoticePosition(f"{fingerprint}-{repeats[fingerprint]}", name, code))
        repeats[fingerprint] += 1
    if not grouped:
        raise UnreadableNoticeFileError("the item file has no data rows")
    result = [replace(notice, positions=tuple(grouped[notice.lot_id])) for notice in notices]
    for notice in result:
        if len(notice.query_text) > MAX_TEXT_CHARS:
            raise InvalidNoticeRowError(
                1, f"combined query for {notice.lot_id} exceeds {MAX_TEXT_CHARS} characters"
            )
    return result


async def read_positions(notices: list[Notice], data: bytes) -> list[Notice]:
    return await asyncio.to_thread(attach_positions, notices, data)
