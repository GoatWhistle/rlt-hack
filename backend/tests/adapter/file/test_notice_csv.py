from datetime import date
from decimal import Decimal

import pytest

from src.adapter.file.notice_csv.reader import CsvNoticeReader, parse_notices
from src.adapter.file.notice_csv.table import detect_delimiter
from src.models.enums import IssueCode
from src.models.errors import (
    MissingNoticeColumnsError,
    TooManyNoticeRowsError,
    UnreadableNoticeFileError,
    UnsupportedNoticeFormatError,
)

HEADER = "lot_id;procedure_name;subject;start_price;publish_date;customer_inn"
TABLE = "\n".join(
    (
        HEADER,
        "4257576;Поставка круп;Крупа гречневая 500 кг;1 000,50;2024-01-18;7807022750",
        "4633163;Оказание услуг связи;Оказание услуг связи;;;",
    )
)


def issues_of(text: str) -> list[tuple[int, IssueCode, str]]:
    return [
        (issue.row, issue.code, issue.value) for issue in parse_notices(text.encode(), 9).issues
    ]


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp1251"])
def test_lots_are_read_in_supported_encodings(encoding: str) -> None:
    notices = parse_notices(TABLE.encode(encoding), 10)
    first, second = notices.lots
    assert (first.lot_id, first.title, first.subject) == (
        "4257576",
        "Поставка круп",
        "Крупа гречневая 500 кг",
    )
    assert (first.start_price, first.publish_date, first.customer_inn) == (
        Decimal("1000.50"),
        date(2024, 1, 18),
        "7807022750",
    )
    assert (second.subject, second.start_price, second.publish_date) == ("", None, None)
    assert notices.issues == ()


@pytest.mark.parametrize("delimiter", [",", "\t"])
def test_other_delimiters_are_detected(delimiter: str) -> None:
    text = f"LOT_ID{delimiter} Procedure_Name \n7{delimiter}Поставка бумаги\n"
    assert detect_delimiter(text) == delimiter
    assert [lot.title for lot in parse_notices(text.encode(), 5).lots] == ["Поставка бумаги"]


def test_quoted_cells_keep_delimiters_quotes_and_line_breaks() -> None:
    text = f'{HEADER}\n\n1;"Права на ""СБиС""; лицензия\nна год";;;;\n2;Бумага;;;;'
    lots = parse_notices(text.encode(), 5).lots
    assert lots[0].title == 'Права на "СБиС"; лицензия на год'
    assert (lots[0].row, lots[1].row) == (3, 5)


def test_broken_rows_become_issues_and_good_rows_survive() -> None:
    text = "\n".join(
        (
            HEADER,
            ";Без номера;;;;",
            "bad id;Плохой номер;;abc;2024-13-01;",
            "1;Хороший;;;;",
            "1;Повтор;;;;",
            "2;;;;;",
            "3;Лишние;;;;;x",
            "4;Только тема;;-5;18.01.2024;",
            "5;;Тема вместо названия;;;",
        )
    )
    assert issues_of(text) == [
        (2, IssueCode.MISSING_LOT_ID, ""),
        (3, IssueCode.BAD_LOT_ID, "bad id"),
        (3, IssueCode.BAD_PRICE, "abc"),
        (3, IssueCode.BAD_DATE, "2024-13-01"),
        (5, IssueCode.DUPLICATE_LOT, "1"),
        (6, IssueCode.MISSING_TITLE, ""),
        (7, IssueCode.COLUMN_COUNT, ""),
        (8, IssueCode.BAD_PRICE, "-5"),
        (8, IssueCode.BAD_DATE, "18.01.2024"),
    ]
    lots = parse_notices(text.encode(), 9).lots
    assert [(lot.lot_id, lot.title) for lot in lots] == [
        ("1", "Хороший"),
        ("5", "Тема вместо названия"),
    ]


@pytest.mark.parametrize(
    ("content", "error"),
    [
        (b"", UnreadableNoticeFileError),
        (b"\n\n;;\n", UnreadableNoticeFileError),
        (HEADER.encode(), UnreadableNoticeFileError),
        (b"lot_id;subject\n1;x", MissingNoticeColumnsError),
        (b"PK\x03\x04binary", UnsupportedNoticeFormatError),
        (b"lot_id\x00;x", UnsupportedNoticeFormatError),
        (b"\x98\x98lot_id", UnreadableNoticeFileError),
        (f"{HEADER}\n1;{'x' * 200_000}".encode(), UnreadableNoticeFileError),
    ],
    ids=["empty", "blank", "header-only", "columns", "zip", "nul", "encoding", "huge-cell"],
)
def test_unusable_files_are_rejected(content: bytes, error: type[Exception]) -> None:
    with pytest.raises(error):
        parse_notices(content, 10)


def test_missing_columns_are_named() -> None:
    with pytest.raises(MissingNoticeColumnsError) as raised:
        parse_notices(b"subject\nx", 10)
    assert raised.value.columns == ("lot_id", "procedure_name")


def test_row_limit_is_enforced() -> None:
    with pytest.raises(TooManyNoticeRowsError) as raised:
        parse_notices(TABLE.encode(), 1)
    assert raised.value.limit == 1


async def test_reader_parses_off_the_event_loop() -> None:
    notices = await CsvNoticeReader().read(TABLE.encode(), 10)
    assert len(notices.lots) == 2
