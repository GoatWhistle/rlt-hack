import asyncio
import time
import tracemalloc

import pytest

from src.adapter.file.notice_csv import reader as reader_module
from src.adapter.file.notice_csv.reader import CsvNoticeReader, parse_notices
from src.adapter.file.notice_csv.table import MAX_COLUMNS, MAX_LINE_CHARS
from src.models.errors import TooManyNoticeRowsError, UnreadableNoticeFileError
from src.models.procurement import NoticeFile

TEN_MEGABYTES = 10 * 1024 * 1024
PEAK_LIMIT = 64 * 1024 * 1024


def test_rejects_header_wider_than_line_limit() -> None:
    content = b"lot_id;procedure_name" + b";" * 1_000_000 + b"\nL1;x\n"
    started = time.perf_counter()
    with pytest.raises(UnreadableNoticeFileError, match="longer than"):
        parse_notices(content, 10)
    assert time.perf_counter() - started < 0.2


def test_rejects_header_with_too_many_columns() -> None:
    content = ("lot_id;procedure_name" + ";c" * MAX_COLUMNS + "\nL1;x\n").encode()
    with pytest.raises(UnreadableNoticeFileError, match="columns"):
        parse_notices(content, 10)


def test_rejects_long_data_line_without_line_breaks() -> None:
    content = b"lot_id;procedure_name\nL1;" + b"x" * (MAX_LINE_CHARS + 1)
    with pytest.raises(UnreadableNoticeFileError, match="longer than"):
        parse_notices(content, 10)


def test_peak_memory_is_bounded() -> None:
    wide = b";" * (MAX_LINE_CHARS - 16) + b"\n"
    lines = TEN_MEGABYTES // len(wide)
    content = b"lot_id;procedure_name\n" + wide * lines + b"L1;x\n"
    assert len(content) > TEN_MEGABYTES - len(wide)
    tracemalloc.start()
    try:
        notices = parse_notices(content, 10)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert [lot.lot_id for lot in notices.lots] == ["L1"]
    assert peak < PEAK_LIMIT


def test_row_limit_stops_reading_early() -> None:
    rows = "".join(f"{index};Поставка\n" for index in range(1, 50))
    content = f"lot_id;procedure_name\n{rows}".encode()
    with pytest.raises(TooManyNoticeRowsError):
        parse_notices(content, 3)


def test_reader_requires_a_positive_parallelism() -> None:
    with pytest.raises(ValueError, match="0"):
        CsvNoticeReader(parallel=0)


async def test_reader_bounds_parallel_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    active = 0
    peak = 0

    def slow(content: bytes, max_rows: int) -> NoticeFile:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        time.sleep(0.05)
        active -= 1
        return NoticeFile(lots=(), issues=())

    monkeypatch.setattr(reader_module, "parse_notices", slow)
    reader = CsvNoticeReader(parallel=1)
    await asyncio.gather(*(reader.read(b"x", 1) for _ in range(3)))
    assert peak == 1
