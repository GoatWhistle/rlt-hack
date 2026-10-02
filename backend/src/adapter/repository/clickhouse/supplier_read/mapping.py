from collections.abc import Mapping, Sequence

from src.adapter.repository.clickhouse.rows import to_uuid
from src.models.enums import NameSource, SupplierRole, VerificationStatus
from src.models.supplier import Supplier

SUPPLIER_COLUMNS = (
    "supplier_id",
    "inn",
    "kpps",
    "name",
    "region",
    "website",
    "contacts",
    "okved_codes",
    "identity_status",
    "identity_evidence_url",
    "role",
    "role_evidence",
    "name_source",
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
        region=str(row[4]),
        website=str(row[5]),
        contacts=_mapping(row[6]),
        okved_codes=_strings(row[7]),
        identity_status=VerificationStatus(str(row[8])),
        identity_evidence_url=str(row[9]),
        role=SupplierRole(str(row[10] or "unknown")),
        role_evidence=str(row[11] or ""),
        name_source=NameSource(str(row[12] or "source")),
    )
