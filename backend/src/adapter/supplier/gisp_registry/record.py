"""Идентичность и действительность версии реестровой записи ГИСП."""

import hashlib
import json
from datetime import date, datetime


def registry_external_id(
    number: str,
    introduced: str,
    basis_number: str,
    company_key: str,
    product: str,
    document_url: str = "",
    writeout_url: str = "",
) -> str:
    immutable_key = (
        number,
        introduced,
        basis_number,
        company_key,
        product,
        document_url,
        writeout_url,
    )
    digest = hashlib.sha256(json.dumps(immutable_key, ensure_ascii=False).encode()).hexdigest()
    return f"{number}:{digest[:20]}"


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            return None


def active_record(status: str, expires: str, ceased: str, today: date) -> bool:
    if ceased:
        return False
    status_key = status.strip().casefold()
    if status_key and status_key not in ("действует", "действующая", "действующий"):
        return False
    end = parse_date(expires) if expires else None
    if expires and end is None:
        return False
    return end >= today if end else bool(status_key)
