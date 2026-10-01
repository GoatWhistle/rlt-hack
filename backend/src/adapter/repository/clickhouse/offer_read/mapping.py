from collections.abc import Mapping, Sequence

from src.adapter.repository.clickhouse.rows import (
    to_datetime,
    to_decimal,
    to_optional_uuid,
    to_uuid,
)
from src.models.enums import (
    Availability,
    ItemType,
    MatchStatus,
    SourceType,
    SupplierRole,
    VerificationStatus,
)
from src.models.offer import Offer
from src.models.offer_evidence import OfferEvidence
from src.models.source import Source

OFFER_FIELDS = (
    "o.offer_id",
    "o.source_id",
    "o.external_id",
    "o.supplier_id",
    "o.seller_status",
    "o.evidence_url",
    "o.url",
    "o.name",
    "substringUTF8(o.description, 1, 1000)",
    "o.item_type",
    "o.brand",
    "o.article",
    "o.attributes",
    "o.source_category",
    "o.okpd2_code",
    "o.price",
    "o.currency",
    "o.unit",
    "o.availability",
    "o.supplier_role",
    "o.role_evidence_text",
    "o.content_hash",
    "o.first_seen_at",
    "o.last_seen_at",
)
SOURCE_FIELDS = (
    "s.source_id",
    "s.name",
    "s.base_url",
    "s.source_type",
    "s.supplier_id",
    "s.ownership_status",
    "s.ownership_evidence_url",
    "s.provider_name",
)
MATCH_FIELDS = ("toString(m.status)", "m.offer_content_hash")
EVIDENCE_FIELDS = ", ".join((*OFFER_FIELDS, *SOURCE_FIELDS, *MATCH_FIELDS))
SOURCE_START = len(OFFER_FIELDS)
MATCH_POSITION = SOURCE_START + len(SOURCE_FIELDS)


def _mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def to_offer(row: Sequence[object]) -> Offer:
    return Offer(
        offer_id=to_uuid(row[0]),
        source_id=to_uuid(row[1]),
        external_id=str(row[2]),
        supplier_id=to_optional_uuid(row[3]),
        seller_status=VerificationStatus(str(row[4])),
        evidence_url=str(row[5]),
        url=str(row[6]),
        name=str(row[7]),
        description=str(row[8]),
        item_type=ItemType(str(row[9])),
        brand=str(row[10]),
        article=str(row[11]),
        attributes=_mapping(row[12]),
        source_category=str(row[13]),
        okpd2_code=str(row[14]),
        price=to_decimal(row[15]),
        currency=str(row[16]),
        unit=str(row[17]),
        availability=Availability(str(row[18])),
        supplier_role=SupplierRole(str(row[19])),
        role_evidence_text=str(row[20]),
        content_hash=str(row[21]),
        first_seen_at=to_datetime(row[22]),
        last_seen_at=to_datetime(row[23]),
    )


def to_source(row: Sequence[object]) -> Source:
    return Source(
        source_id=to_uuid(row[0]),
        name=str(row[1]),
        base_url=str(row[2]),
        source_type=SourceType(str(row[3])),
        supplier_id=to_optional_uuid(row[4]),
        ownership_status=VerificationStatus(str(row[5])),
        ownership_evidence_url=str(row[6]),
        provider_name=str(row[7]),
    )


def to_offer_evidence(row: Sequence[object]) -> OfferEvidence:
    return OfferEvidence(
        offer=to_offer(row[:SOURCE_START]),
        source=to_source(row[SOURCE_START:MATCH_POSITION]),
        match_status=MatchStatus(str(row[MATCH_POSITION])),
        matched_content_hash=str(row[MATCH_POSITION + 1] or ""),
    )
