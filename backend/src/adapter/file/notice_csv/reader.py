import asyncio
from collections.abc import Mapping
from functools import partial

from src.adapter.file.notice_csv.decode import decode_notices
from src.adapter.file.notice_csv.rows import read_lot
from src.adapter.file.notice_csv.table import CsvRecord, read_records
from src.models.enums import IssueCode
from src.models.errors import (
    MissingNoticeColumnsError,
    TooManyNoticeRowsError,
    UnreadableNoticeFileError,
)
from src.models.procurement import NoticeFile, ProcurementLot, RowIssue

REQUIRED_COLUMNS = ("lot_id", "procedure_name")


def normalize_header(cell: str) -> str:
    return cell.removeprefix("﻿").strip().lower()


def parse_notices(content: bytes, max_rows: int) -> NoticeFile:
    records = read_records(decode_notices(content))
    if not records:
        raise UnreadableNoticeFileError("the file is empty")
    head, *data = records
    header = [normalize_header(cell) for cell in head.cells]
    missing = tuple(column for column in REQUIRED_COLUMNS if column not in header)
    if missing:
        raise MissingNoticeColumnsError(missing)
    if not data:
        raise UnreadableNoticeFileError("the file has no data rows")
    if len(data) > max_rows:
        raise TooManyNoticeRowsError(max_rows)
    return _notices(header, data)


def _cell(positions: Mapping[str, int], cells: tuple[str, ...], column: str) -> str:
    index = positions.get(column)
    return cells[index].strip() if index is not None and index < len(cells) else ""


def _notices(header: list[str], data: list[CsvRecord]) -> NoticeFile:
    positions = {name: index for index, name in reversed(list(enumerate(header)))}
    lots: list[ProcurementLot] = []
    issues: list[RowIssue] = []
    seen: set[str] = set()
    for record in data:
        if len(record.cells) > len(header):
            issues.append(RowIssue(record.line, IssueCode.COLUMN_COUNT))
            continue
        outcome = read_lot(record.line, partial(_cell, positions, record.cells), seen)
        if isinstance(outcome, ProcurementLot):
            lots.append(outcome)
        else:
            issues.extend(outcome)
    return NoticeFile(lots=tuple(lots), issues=tuple(issues))


class CsvNoticeReader:
    async def read(self, content: bytes, max_rows: int) -> NoticeFile:
        return await asyncio.to_thread(parse_notices, content, max_rows)
