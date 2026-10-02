from src.adapter.repository.clickhouse.offer_read.mapping import to_offer
from src.adapter.repository.clickhouse.supplier_read.mapping import to_supplier
from src.models.enums import SupplierRole, VerificationStatus
from tests.fakes.domain import uid


def test_supplier_rows_tolerate_missing_collections() -> None:
    row = (
        str(uid("alpha")),
        None,
        None,
        "ООО «Альфа»",
        "78",
        "",
        None,
        None,
        "conflict",
        "",
        None,
        None,
        None,
    )
    supplier = to_supplier(row)
    assert (supplier.inn, supplier.kpps, supplier.contacts) == (None, (), {})
    assert supplier.identity_status == VerificationStatus.CONFLICT
    assert (supplier.role, supplier.role_evidence) == (SupplierRole.UNKNOWN, "")


def test_offer_rows_tolerate_missing_collections() -> None:
    row = [
        str(uid("offer")),
        str(uid("source")),
        "external",
        None,
        "unverified",
        "",
        "https://example.org/offer",
        "Товар",
        "",
        "goods",
        "",
        "",
        None,
        "",
        "",
        None,
        "",
        "",
        "unknown",
        "unknown",
        "",
        "",
        "2026-09-29 08:00:00.000",
        "2026-09-29 08:00:00.000",
    ]
    offer = to_offer(row)
    assert (offer.supplier_id, offer.price, offer.attributes) == (None, None, {})
