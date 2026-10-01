import csv
import io
from dataclasses import dataclass

from src.models.errors import UnreadableNoticeFileError

DELIMITERS = (";", ",", "\t")


@dataclass(frozen=True, slots=True)
class CsvRecord:
    line: int
    cells: tuple[str, ...]

    @property
    def blank(self) -> bool:
        return not any(cell.strip() for cell in self.cells)


def detect_delimiter(text: str) -> str:
    first_line = text.split("\n", 1)[0]
    scores = [len(first_line.split(delimiter)) for delimiter in DELIMITERS]
    return DELIMITERS[scores.index(max(scores))]


def read_records(text: str) -> list[CsvRecord]:
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=detect_delimiter(text))
    records: list[CsvRecord] = []
    start = 1
    try:
        for cells in reader:
            record = CsvRecord(start, tuple(cells))
            start = reader.line_num + 1
            if not record.blank:
                records.append(record)
    except csv.Error as error:
        raise UnreadableNoticeFileError(str(error)) from error
    return records
