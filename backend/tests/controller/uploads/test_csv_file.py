import asyncio
import time
import tracemalloc

import pytest

from src.controller.uploads import csv_file
from src.controller.uploads.csv_file import (
    MAX_COLUMNS,
    MAX_LINE_CHARS,
    NoticeReader,
    decode_notices,
)
from src.models.errors import (
    InvalidNoticeRowError,
    MissingNoticeColumnsError,
    TooManyNoticeRowsError,
    UnreadableNoticeFileError,
    UnsupportedNoticeFormatError,
)
from src.models.upload import Notice

TWO_MEGABYTES = 2 * 1024 * 1024
PEAK_LIMIT = 32 * 1024 * 1024


def test_reads_lots_with_any_supported_delimiter_and_encoding() -> None:
    assert decode_notices(b"lot_id,procedure_name,subject\nL1,paper,A4\n") == [
        Notice("L1", "paper", "A4")
    ]
    assert decode_notices("lot_id;procedure_name\nL1;Бумага".encode("cp1251")) == [
        Notice("L1", "Бумага")
    ]
    tabbed = "lot_id\tprocedure_name\nL1\tx\n\n".encode("utf-8-sig")
    assert decode_notices(tabbed) == [Notice("L1", "x")]


def test_subject_stands_in_for_an_empty_title() -> None:
    assert decode_notices(b"lot_id;procedure_name;subject\nL1;;cable\n") == [Notice("L1", "cable")]


def test_rejects_binary_documents() -> None:
    for content in (b"PK\x03\x04rest", b"%PDF-1.7", b"lot_id\x00procedure_name"):
        with pytest.raises(UnsupportedNoticeFormatError):
            decode_notices(content)


def test_rejects_unknown_encoding() -> None:
    with pytest.raises(UnreadableNoticeFileError, match="encoding"):
        decode_notices(b"lot_id;procedure_name\nL1;\x98\xff\n")


def test_rejects_header_wider_than_line_limit_quickly() -> None:
    content = b"lot_id;procedure_name" + b";" * 1_000_000 + b"\nL1;x\n"
    started = time.perf_counter()
    with pytest.raises(UnreadableNoticeFileError, match="longer than"):
        decode_notices(content)
    assert time.perf_counter() - started < 0.2


def test_rejects_header_with_too_many_columns() -> None:
    content = ("lot_id;procedure_name" + ";c" * MAX_COLUMNS + "\nL1;x\n").encode()
    with pytest.raises(UnreadableNoticeFileError, match="columns"):
        decode_notices(content)


def test_rejects_long_data_line_without_line_breaks() -> None:
    content = b"lot_id;procedure_name\nL1;" + b"x" * (MAX_LINE_CHARS + 1)
    with pytest.raises(UnreadableNoticeFileError, match="longer than"):
        decode_notices(content)


def test_peak_memory_is_bounded() -> None:
    blank = b";" * (MAX_LINE_CHARS - 16) + b"\n"
    content = b"lot_id;procedure_name\n" + blank * (TWO_MEGABYTES // len(blank)) + b"L1;x\n"
    tracemalloc.start()
    try:
        notices = decode_notices(content)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert notices == [Notice("L1", "x")]
    assert peak < PEAK_LIMIT


def test_row_limit_stops_reading_early() -> None:
    rows = "".join(f"L{index};paper\n" for index in range(50))
    with pytest.raises(TooManyNoticeRowsError, match="3"):
        decode_notices(f"lot_id;procedure_name\n{rows}".encode(), 3)


def test_missing_columns_are_named() -> None:
    with pytest.raises(MissingNoticeColumnsError) as raised:
        decode_notices(b"title;subject\nx;y\n")
    assert raised.value.columns == ("lot_id", "procedure_name")


@pytest.mark.parametrize(
    ("content", "line", "reason"),
    [
        (b"lot_id;procedure_name\nL1;a\nL1;b\n", 3, "repeated"),
        (b"lot_id;procedure_name\nL 1;a\n", 2, "lot_id"),
        (b"lot_id;procedure_name\n\nL1;\n", 3, "procedure_name"),
        (b"lot_id;procedure_name\nL1;a;extra\n", 2, "cells"),
        (b"lot_id;procedure_name\nL1;" + b"x" * 4000 + b"\n", 2, "longer"),
    ],
    ids=["repeated", "pattern", "title", "cells", "length"],
)
def test_invalid_rows_name_their_line(content: bytes, line: int, reason: str) -> None:
    with pytest.raises(InvalidNoticeRowError, match=reason) as raised:
        decode_notices(content)
    assert raised.value.line == line


@pytest.mark.parametrize("content", [b"", b"\n\n", b"lot_id;procedure_name\n;;\n"])
def test_empty_files_are_unreadable(content: bytes) -> None:
    with pytest.raises(UnreadableNoticeFileError):
        decode_notices(content)


def test_broken_quoting_is_unreadable() -> None:
    quoted = (b"x" * 60_000 + b"\n") * 3
    with pytest.raises(UnreadableNoticeFileError, match="field"):
        decode_notices(b'lot_id;procedure_name\nL1;"' + quoted + b'"\n')


def test_reader_requires_a_positive_parallelism() -> None:
    with pytest.raises(ValueError, match="0"):
        NoticeReader(parallel=0)


async def test_reader_bounds_parallel_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    active = 0
    peak = 0

    def slow(content: bytes, max_rows: int) -> list[Notice]:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        time.sleep(0.05)
        active -= 1
        return []

    monkeypatch.setattr(csv_file, "decode_notices", slow)
    reader = NoticeReader(parallel=1)
    await asyncio.gather(*(reader.read(b"x") for _ in range(3)))
    assert peak == 1
