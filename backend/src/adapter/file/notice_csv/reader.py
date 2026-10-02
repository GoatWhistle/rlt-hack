import asyncio
from collections.abc import Iterator, Mapping
from functools import partial

from src.adapter.file.notice_csv.decode import decode_notices
from src.adapter.file.notice_csv.rows import read_lot
from src.adapter.file.notice_csv.table import CsvRecord, check_header, iter_records
from src.models.enums import IssueCode
from src.models.errors import (
    MissingNoticeColumnsError,
    TooManyNoticeRowsError,
    UnreadableNoticeFileError,
)
from src.models.procurement import NoticeFile, ProcurementLot, RowIssue

REQUIRED_COLUMNS = ("lot_id", "procedure_name")
DEFAULT_PARALLEL_READS = 2


def normalize_header(cell: str) -> str:
    return cell.removeprefix("﻿").strip().lower()


def parse_notices(content: bytes, max_rows: int) -> NoticeFile:
    records = iter_records(decode_notices(content))
    head = next(records, None)
    if head is None:
        raise UnreadableNoticeFileError("the file is empty")
    check_header(head)
    header = [normalize_header(cell) for cell in head.cells]
    missing = tuple(column for column in REQUIRED_COLUMNS if column not in header)
    if missing:
        raise MissingNoticeColumnsError(missing)
    return _notices(header, records, max_rows)


def _cell(positions: Mapping[str, int], cells: tuple[str, ...], column: str) -> str:
    index = positions.get(column)
    return cells[index].strip() if index is not None and index < len(cells) else ""


def _notices(header: list[str], records: Iterator[CsvRecord], max_rows: int) -> NoticeFile:
    positions = {name: index for index, name in reversed(list(enumerate(header)))}
    lots: list[ProcurementLot] = []
    issues: list[RowIssue] = []
    seen: set[str] = set()
    rows = 0
    for record in records:
        rows += 1
        if rows > max_rows:
            raise TooManyNoticeRowsError(max_rows)
        if len(record.cells) > len(header):
            issues.append(RowIssue(record.line, IssueCode.COLUMN_COUNT))
            continue
        outcome = read_lot(record.line, partial(_cell, positions, record.cells), seen)
        if isinstance(outcome, ProcurementLot):
            lots.append(outcome)
        else:
            issues.extend(outcome)
    if not rows:
        raise UnreadableNoticeFileError("the file has no data rows")
    return NoticeFile(lots=tuple(lots), issues=tuple(issues))


class CsvNoticeReader:
    def __init__(self, parallel: int = DEFAULT_PARALLEL_READS) -> None:
        if parallel < 1:
            raise ValueError(parallel)
        self._slots = asyncio.Semaphore(parallel)

    async def read(self, content: bytes, max_rows: int) -> NoticeFile:
        async with self._slots:
            return await asyncio.to_thread(parse_notices, content, max_rows)
