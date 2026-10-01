import csv
import io
import re

from src.models.upload import Notice


def decode_notices(data: bytes) -> list[Notice]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1251")
    first_line = text.splitlines()[0] if text else ""
    separator = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=separator)
    if reader.fieldnames is None:
        raise ValueError("empty CSV")
    reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
    if not {"lot_id", "procedure_name"}.issubset(reader.fieldnames):
        raise ValueError("missing columns")
    result = []
    seen = set()
    for row in reader:
        lot_id = (row.get("lot_id") or "").strip()
        title = (row.get("procedure_name") or row.get("subject") or "").strip()
        subject = (row.get("subject") or "").strip()
        if (
            None in row
            or not re.fullmatch(r"[0-9A-Za-z_-]{1,128}", lot_id)
            or lot_id in seen
            or not title
            or len(title) + len(subject) > 3999
        ):
            raise ValueError("invalid CSV row")
        seen.add(lot_id)
        result.append(Notice(lot_id, title, subject if subject != title else ""))
        if len(result) > 20:
            raise ValueError("too many rows")
    if not result:
        raise ValueError("empty CSV")
    return result
