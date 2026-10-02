"""Преобразование публичных JSON-страниц реестров продукции и организаций."""

import json
from datetime import datetime
from typing import Any

from src.adapter.supplier import identity
from src.adapter.supplier.errors import ContentFormatError
from src.adapter.supplier.gisp_registry.record import active_record, registry_external_id
from src.adapter.supplier.inn import normalize_inn
from src.models.catalog.offer import Offer
from src.models.catalog.source import Source
from src.models.catalog.supplier import Supplier
from src.models.enums import ItemType, SupplierRole, VerificationStatus


def _value(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return " ".join(str(value).split())


def parse_organization(item: dict[str, Any], source: Source) -> Supplier:
    name = _value(item, "org_name")
    inn = normalize_inn(_value(item, "org_inn"))
    ogrn = _value(item, "org_ogrn")
    url = _value(item, "gisp_url")
    if not name or not (inn or ogrn or url):
        raise ContentFormatError("ГИСП: организация без названия и устойчивого ключа")
    key = inn or ogrn or url
    return Supplier(
        supplier_id=identity.supplier_id(inn, source.source_id, key),
        name=name,
        inn=inn,
        region=_value(item, "org_region_name"),
        contacts={"ogrn": ogrn} if ogrn else {},
        identity_status=VerificationStatus.UNVERIFIED,
        identity_evidence_url=url or source.base_url,
    )


def parse_product(
    item: dict[str, Any], source: Source, observed_at: datetime
) -> tuple[Supplier, Offer]:
    name = _value(item, "_product_name")
    company = _value(item, "_org_name")
    number = _value(item, "_product_reg_number_2023")
    old_number = _value(item, "_product_reg_number_2022")
    if not number:
        number = f"old:{old_number}" if old_number else ""
    if not name or not company or not number:
        raise ContentFormatError("ГИСП: неполная запись продукции")
    inn = normalize_inn(_value(item, "_org_inn"))
    ogrn = _value(item, "_org_ogrn")
    company_url = _value(item, "_gisp_url")
    company_key = inn or ogrn or company_url or f"registry:{number}"
    supplier_uuid = identity.supplier_id(inn, source.source_id, company_key)
    supplier = Supplier(
        supplier_id=supplier_uuid,
        name=company,
        inn=inn,
        contacts={"ogrn": ogrn} if ogrn else {},
        identity_status=VerificationStatus.UNVERIFIED,
        identity_evidence_url=company_url or source.base_url,
    )
    introduced = _value(item, "_res_date")
    expires = _value(item, "_res_valid_till")
    ceased = _value(item, "_res_end_date")
    active = active_record("", expires, ceased, observed_at.date())
    attributes = {
        key: value
        for key, value in (
            ("registry_number", number),
            ("initial_registry_number", old_number),
            ("registry_introduced", introduced),
            ("registry_expires", expires),
            ("registry_ceased", ceased),
            ("digital_passport_number", _value(item, "_ektru_dp")),
            ("tnved", _value(item, "_product_tnved")),
            ("standard", _value(item, "_product_spec")),
            ("points", _value(item, "_product_score_value")),
            ("percent", _value(item, "_product_percentage")),
            ("compliance", _value(item, "_product_score_desc")),
            ("ai", _value(item, "_is_ai_tpp")),
            ("hightech", _value(item, "_high_tech")),
            ("trusted_pak", _value(item, "_is_pak")),
            ("basis_name", _value(item, "_basedondoc_name")),
            ("basis_date", _value(item, "_basedondoc_date")),
            ("basis_number", _value(item, "_basedondoc_num")),
            ("basis_expires", _value(item, "_basedondoc_exp")),
            ("department", _value(item, "_res_mptdep_name")),
            ("conclusion_number", _value(item, "_res_number")),
            ("conclusion_document", _value(item, "_res_scan_url")),
            ("writeout_url", _value(item, "_product_writeout_url")),
            ("ru_pak_info", _value(item, "_product_ru_pak_info")),
            ("eu_pak_info", _value(item, "_product_eu_pak_info")),
            ("certificate_info", _value(item, "_product_sert_pak_info")),
        )
        if value
    }
    external_id = registry_external_id(
        number,
        introduced,
        _value(item, "_basedondoc_num"),
        company_key,
        name,
        _value(item, "_res_scan_url"),
        _value(item, "_product_writeout_url"),
    )
    offer = Offer(
        offer_id=identity.offer_id(source.source_id, external_id),
        source_id=source.source_id,
        external_id=external_id,
        url=_value(item, "_product_gisp_url") or source.base_url,
        name=name,
        first_seen_at=observed_at,
        last_seen_at=observed_at,
        supplier_id=supplier_uuid,
        seller_status=VerificationStatus.UNVERIFIED,
        evidence_url=company_url or source.base_url,
        item_type=ItemType.GOODS,
        okpd2_code=_value(item, "_product_okpd2"),
        attributes=attributes,
        supplier_role=SupplierRole.MANUFACTURER if active else SupplierRole.UNKNOWN,
        role_evidence_text="Действующая запись реестра" if active else "",
        content_hash=identity.offer_content_hash(
            name=name,
            item_type=str(ItemType.GOODS),
            okpd2_code=_value(item, "_product_okpd2"),
            attributes=attributes,
        ),
    )
    return supplier, offer


def parse_organizations(items: list[dict[str, Any]], source: Source) -> list[Supplier]:
    return [parse_organization(item, source) for item in items]


def parse_products(
    items: list[dict[str, Any]], source: Source, observed_at: datetime
) -> list[tuple[Supplier, Offer]]:
    return [parse_product(item, source, observed_at) for item in items]
