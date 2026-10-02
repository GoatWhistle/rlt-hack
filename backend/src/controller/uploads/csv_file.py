import asyncio
import csv
import re
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation

from src.models.errors import (
    InvalidNoticeRowError,
    MissingNoticeColumnsError,
    UnreadableNoticeFileError,
    UnsupportedNoticeFormatError,
)
from src.models.operations.upload import Notice

MAX_LINE_CHARS = 64 * 1024
MAX_COLUMNS = 64
MAX_TEXT_CHARS = 3999
PARALLEL_READS = 2
REQUIRED_COLUMNS = ("lot_id", "procedure_name")
DELIMITERS = (",", ";", "\t")
BINARY_SIGNATURES = (b"PK\x03\x04", b"\xd0\xcf\x11\xe0", b"%PDF")
SNIFF_BYTES = 4096
BOM = chr(0xFEFF)
LOT_ID = re.compile(r"[0-9A-Za-z_-]{1,128}")
LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+\Z")

Record = tuple[int, list[str]]


def decode_text(data: bytes) -> str:
    if data.startswith(BINARY_SIGNATURES) or b"\x00" in data[:SNIFF_BYTES]:
        raise UnsupportedNoticeFormatError
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("cp1251")
    except UnicodeDecodeError as error:
        raise UnreadableNoticeFileError("unknown text encoding") from error


def delimiter_of(text: str) -> str:
    first_line = text[: MAX_LINE_CHARS + 1].split("\n", 1)[0]
    scores = [first_line.count(delimiter) for delimiter in DELIMITERS]
    return DELIMITERS[scores.index(max(scores))]


def bounded_lines(text: str) -> Iterator[str]:
    for match in LINE.finditer(text):
        start, end = match.span()
        if end - start > MAX_LINE_CHARS:
            raise UnreadableNoticeFileError(f"a line is longer than {MAX_LINE_CHARS} characters")
        yield match.group()


def records(text: str) -> Iterator[Record]:
    reader = csv.reader(bounded_lines(text), delimiter=delimiter_of(text))
    line = 1
    try:
        for cells in reader:
            start, line = line, reader.line_num + 1
            if any(cell.strip() for cell in cells):
                yield start, cells
    except csv.Error as error:
        raise UnreadableNoticeFileError(str(error)) from error


def columns_of(cells: list[str]) -> dict[str, int]:
    if len(cells) > MAX_COLUMNS:
        raise UnreadableNoticeFileError(f"the header has more than {MAX_COLUMNS} columns")
    names = [cell.removeprefix(BOM).strip().lower() for cell in cells]
    missing = tuple(column for column in REQUIRED_COLUMNS if column not in names)
    if missing:
        raise MissingNoticeColumnsError(missing)
    return {name: index for index, name in enumerate(names)}


def notice_of(record: Record, columns: dict[str, int], width: int, seen: set[str]) -> Notice:
    line, cells = record
    if len(cells) > width:
        raise InvalidNoticeRowError(line, "the row has more cells than the header")

    def cell(name: str) -> str:
        index = columns.get(name)
        return cells[index].strip() if index is not None and index < len(cells) else ""

    lot_id = cell("lot_id")
    subject = cell("subject")
    title = cell("procedure_name") or subject
    if not LOT_ID.fullmatch(lot_id):
        raise InvalidNoticeRowError(line, "lot_id must be 1-128 latin letters, digits, _ or -")
    if lot_id in seen:
        raise InvalidNoticeRowError(line, f"lot_id {lot_id} is repeated")
    if not title:
        raise InvalidNoticeRowError(line, "procedure_name is empty")
    if len(title) + len(subject) > MAX_TEXT_CHARS:
        raise InvalidNoticeRowError(line, f"the text is longer than {MAX_TEXT_CHARS} characters")
    seen.add(lot_id)
    customer = cell("customer_inn")
    if customer and not re.fullmatch(r"[0-9]{10}|[0-9]{12}", customer):
        raise InvalidNoticeRowError(line, "invalid customer INN")
    raw_price = cell("start_price").replace("\u00a0", "").replace(" ", "")
    try:
        price = Decimal(raw_price.replace(",", ".")) if raw_price else None
    except InvalidOperation as error:
        raise InvalidNoticeRowError(line, "invalid start price") from error
    if price is not None and (not price.is_finite() or price < 0):
        raise InvalidNoticeRowError(line, "invalid start price")
    region = cell("delivery_region")
    if region and not re.fullmatch(r"[0-9]{2}", region):
        raise InvalidNoticeRowError(line, "invalid delivery region")
    return Notice(lot_id, title, subject if subject != title else "", customer, price, region)


def decode_notices(data: bytes) -> list[Notice]:
    rows = records(decode_text(data))
    head = next(rows, None)
    if head is None:
        raise UnreadableNoticeFileError("the file is empty")
    columns = columns_of(head[1])
    seen: set[str] = set()
    notices: list[Notice] = []
    for record in rows:
        notices.append(notice_of(record, columns, len(head[1]), seen))
    if not notices:
        raise UnreadableNoticeFileError("the file has no data rows")
    return notices


class NoticeReader:
    def __init__(self, parallel: int = PARALLEL_READS) -> None:
        if parallel < 1:
            raise ValueError(parallel)
        self._slots = asyncio.Semaphore(parallel)

    async def read(self, data: bytes) -> list[Notice]:
        async with self._slots:
            return await asyncio.to_thread(decode_notices, data)
