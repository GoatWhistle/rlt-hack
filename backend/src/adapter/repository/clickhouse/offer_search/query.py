from collections.abc import Mapping
from dataclasses import dataclass, field

from src.models.enums import ItemType
from src.models.search import SearchFilters

SELECT_CANDIDATES = (
    "SELECT o.offer_id, o.supplier_id, o.search_text "
    "FROM {db}.offers_current AS o {join}"
    "WHERE o.availability != 'unavailable' AND isNotNull(o.supplier_id) "
    "AND multiSearchAny(o.search_text, {{needles:Array(String)}}) {conditions}"
    "ORDER BY arrayCount(position -> position > 0, "
    "multiSearchAllPositions(o.search_text, {{needles:Array(String)}})) DESC, "
    "o.last_seen_at DESC, o.offer_id "
    "LIMIT {{per_supplier:UInt32}} BY o.supplier_id "
    "LIMIT {{pool:UInt32}}"
)
OFFERS_PER_SUPPLIER = 20
REGION_JOIN = "LEFT JOIN {db}.suppliers_current AS s ON s.supplier_id = o.supplier_id "
REGION_CONDITION = "AND has({regions:Array(String)}, s.region) "
TYPE_CONDITION = "AND o.item_type IN ({item_type:String}, 'unknown') "


@dataclass(frozen=True, slots=True)
class CandidateQuery:
    statement: str
    parameters: Mapping[str, object] = field(default_factory=dict)


def candidate_query(
    database: str, needles: tuple[str, ...], filters: SearchFilters, pool: int
) -> CandidateQuery:
    parameters: dict[str, object] = {
        "needles": list(needles),
        "pool": pool,
        "per_supplier": OFFERS_PER_SUPPLIER,
    }
    join = ""
    conditions = ""
    if filters.regions:
        join = REGION_JOIN.format(db=database)
        conditions += REGION_CONDITION
        parameters["regions"] = list(filters.regions)
    if filters.item_type is not None and filters.item_type != ItemType.UNKNOWN:
        conditions += TYPE_CONDITION
        parameters["item_type"] = str(filters.item_type)
    statement = SELECT_CANDIDATES.format(db=database, join=join, conditions=conditions)
    return CandidateQuery(statement, parameters)
