"""Общие фрагменты запросов аналитики: одно определение на показатель."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from src.models.analytics.filters import AnalyticsFilters, FreshnessPolicy
from src.models.analytics.records import RecordProblem

KNOWN = "(o.last_seen_at > toDateTime64('1971-01-01 00:00:00', 3, 'UTC'))"
FRESH = (
    "(o.last_seen_at + toIntervalDay(if(s.source_type = 'registry', "
    "{registry_days:UInt16}, {offer_days:UInt16})) >= {as_of:DateTime64(3)})"
)
FRESH_KNOWN = f"({KNOWN} AND {FRESH})"
STALE = f"({KNOWN} AND NOT {FRESH})"
UNKNOWN_AGE = f"(NOT {KNOWN})"
SEARCHABLE = "(o.availability != 'unavailable' AND isNotNull(o.supplier_id))"
VERIFIED = "(o.seller_status = 'verified' AND isNotNull(o.supplier_id))"
COMMERCIAL = "(s.source_type IN ('directory', 'website', 'feed', 'price_list'))"
HAS_CODE = "(o.okpd2_code != '')"
HAS_ATTRIBUTES = "(notEmpty(o.attributes) OR notEmpty(o.normalized_attributes))"
SYSTEM_ASSIGNED = "(o.classification_method != 'none')"
SOURCE_REPORTED = f"(o.classification_method = 'none' AND {HAS_CODE})"

AGE_BUCKET = (
    f"multiIf({UNKNOWN_AGE}, 'unknown', "
    "dateDiff('second', o.last_seen_at, {as_of:DateTime64(3)}) < 86400, 'd1', "
    "dateDiff('second', o.last_seen_at, {as_of:DateTime64(3)}) < 604800, 'd7', "
    "dateDiff('second', o.last_seen_at, {as_of:DateTime64(3)}) < 2592000, 'd30', 'older')"
)
ORIGIN = f"multiIf({SYSTEM_ASSIGNED}, 'system', {SOURCE_REPORTED}, 'source', 'absent')"

BASE = (
    "FROM {db}.offers_current AS o "
    "INNER JOIN {db}.sources_current AS s ON s.source_id = o.source_id "
    "LEFT JOIN {db}.suppliers_current AS c ON c.supplier_id = o.supplier_id "
    "WHERE 1 {scope}"
)

PROBLEMS: Mapping[RecordProblem, str] = {
    RecordProblem.STALE: STALE,
    RecordProblem.UNKNOWN_AGE: UNKNOWN_AGE,
    RecordProblem.NO_CATEGORY: f"(NOT {HAS_CODE})",
    RecordProblem.NO_PRICE: f"({COMMERCIAL} AND isNull(o.price))",
    RecordProblem.NO_SUPPLIER: "isNull(o.supplier_id)",
    RecordProblem.UNVERIFIED_SELLER: "(isNotNull(o.supplier_id) AND o.seller_status != 'verified')",
    RecordProblem.NO_ATTRIBUTES: f"(NOT {HAS_ATTRIBUTES})",
}


def scope_of(
    filters: AnalyticsFilters, source_column: str = "o.source_id", *, region: bool = True
) -> tuple[str, dict[str, Any]]:
    clauses: list[str] = []
    parameters: dict[str, Any] = {}
    if filters.source_id is not None:
        clauses.append(f"{source_column} = {{source_id:UUID}}")
        parameters["source_id"] = str(filters.source_id)
    if filters.source_type is not None:
        clauses.append("s.source_type = {source_type:String}")
        parameters["source_type"] = str(filters.source_type)
    if region and filters.region:
        clauses.append("c.region = {region:String}")
        parameters["region"] = filters.region
    return "".join(f" AND {clause}" for clause in clauses), parameters


def policy_parameters(policy: FreshnessPolicy, as_of: datetime) -> dict[str, Any]:
    return {
        "offer_days": policy.offer_days,
        "registry_days": policy.registry_days,
        "as_of": as_of,
    }
