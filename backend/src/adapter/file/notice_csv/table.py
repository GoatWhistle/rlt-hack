import csv
import re
from collections.abc import Iterator
from dataclasses import dataclass

from src.models.errors import UnreadableNoticeFileError

DELIMITERS = (";", ",", "\t")
MAX_LINE_CHARS = 64 * 1024
MAX_COLUMNS = 64
LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+\Z")


@dataclass(frozen=True, slots=True)
class CsvRecord:
    line: int
    cells: tuple[str, ...]

    @property
    def blank(self) -> bool:
        return not any(cell.strip() for cell in self.cells)


def detect_delimiter(text: str) -> str:
    first_line = text[: MAX_LINE_CHARS + 1].split("\n", 1)[0]
    scores = [first_line.count(delimiter) for delimiter in DELIMITERS]
    return DELIMITERS[scores.index(max(scores))]


def bounded_lines(text: str) -> Iterator[str]:
    for match in LINE.finditer(text):
        start, end = match.span()
        if end - start > MAX_LINE_CHARS:
            raise UnreadableNoticeFileError(f"a line is longer than {MAX_LINE_CHARS} characters")
        yield match.group()


def iter_records(text: str) -> Iterator[CsvRecord]:
    reader = csv.reader(bounded_lines(text), delimiter=detect_delimiter(text))
    start = 1
    try:
        for cells in reader:
            record = CsvRecord(start, tuple(cells))
            start = reader.line_num + 1
            if not record.blank:
                yield record
    except csv.Error as error:
        raise UnreadableNoticeFileError(str(error)) from error


def check_header(record: CsvRecord) -> None:
    if len(record.cells) > MAX_COLUMNS:
        raise UnreadableNoticeFileError(f"the header has more than {MAX_COLUMNS} columns")
