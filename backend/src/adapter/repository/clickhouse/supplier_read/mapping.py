from collections.abc import Mapping, Sequence

from src.adapter.repository.clickhouse.rows import to_uuid
from src.models.enums import VerificationStatus
from src.models.supplier import Supplier

SUPPLIER_COLUMNS = (
    "supplier_id",
    "inn",
    "kpps",
    "name",
    "legal_status",
    "region",
    "website",
    "contacts",
    "okved_codes",
    "identity_status",
    "identity_evidence_url",
)


def _strings(value: object) -> tuple[str, ...]:
    return tuple(str(item) for item in value) if isinstance(value, list | tuple) else ()


def _mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def to_supplier(row: Sequence[object]) -> Supplier:
    return Supplier(
        supplier_id=to_uuid(row[0]),
        inn=None if row[1] is None else str(row[1]),
        kpps=_strings(row[2]),
        name=str(row[3]),
        legal_status=str(row[4]),
        region=str(row[5]),
        website=str(row[6]),
        contacts=_mapping(row[7]),
        okved_codes=_strings(row[8]),
        identity_status=VerificationStatus(str(row[9])),
        identity_evidence_url=str(row[10]),
    )
