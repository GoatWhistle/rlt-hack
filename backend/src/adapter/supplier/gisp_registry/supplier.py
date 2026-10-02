"""Объединение реквизитов одной компании из двух перечней ГИСП."""

from src.models.catalog.supplier import Supplier


def merge_supplier(primary: Supplier, secondary: Supplier) -> Supplier:
    """Публичный перечень приоритетен; выгрузка дополняет пустые поля."""
    if primary.supplier_id != secondary.supplier_id:
        raise ValueError("Нельзя объединить разные компании")
    return Supplier(
        supplier_id=primary.supplier_id,
        name=primary.name or secondary.name,
        inn=primary.inn or secondary.inn,
        kpps=tuple(dict.fromkeys((*primary.kpps, *secondary.kpps))),
        region=primary.region or secondary.region,
        website=primary.website or secondary.website,
        contacts={**secondary.contacts, **primary.contacts},
        okved_codes=tuple(dict.fromkeys((*primary.okved_codes, *secondary.okved_codes))),
        identity_status=primary.identity_status,
        identity_evidence_url=primary.identity_evidence_url or secondary.identity_evidence_url,
    )
