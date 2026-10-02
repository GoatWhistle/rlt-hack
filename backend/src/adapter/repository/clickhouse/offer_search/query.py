from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from src.adapter.repository.clickhouse.retrieval.prefixes import term_match
from src.models.enums import ItemType
from src.models.search import SearchFilters

SEARCH_COLUMN = "o.search_text"
SELECT_CANDIDATES = (
    "SELECT o.offer_id, o.supplier_id, o.search_terms, {columns} "
    "FROM {db}.offers_current AS o {join}"
    "WHERE o.availability != 'unavailable' AND isNotNull(o.supplier_id) "
    "AND {matched} {conditions}"
    "ORDER BY {hits} DESC, o.last_seen_at DESC, o.offer_id "
    "LIMIT {{pool:UInt32}}"
)
REGION_JOIN = "LEFT JOIN {db}.suppliers_current AS s ON s.supplier_id = o.supplier_id "
REGION_CONDITION = "AND has({regions:Array(String)}, s.region) "
TYPE_CONDITION = "AND o.item_type IN ({item_type:String}, 'unknown') "


@dataclass(frozen=True, slots=True)
class CandidateQuery:
    statement: str
    parameters: Mapping[str, object] = field(default_factory=dict)


def candidate_query(
    database: str, terms: Sequence[str], filters: SearchFilters, pool: int
) -> CandidateQuery:
    match = term_match(SEARCH_COLUMN, terms)
    parameters: dict[str, object] = {**match.parameters, "pool": pool}
    join = ""
    conditions = ""
    if filters.regions:
        join = REGION_JOIN.format(db=database)
        conditions += REGION_CONDITION
        parameters["regions"] = list(filters.regions)
    if filters.item_type is not None and filters.item_type != ItemType.UNKNOWN:
        conditions += TYPE_CONDITION
        parameters["item_type"] = str(filters.item_type)
    statement = SELECT_CANDIDATES.format(
        db=database,
        join=join,
        conditions=conditions,
        columns=match.columns,
        matched=match.matched,
        hits=match.hits,
    )
    return CandidateQuery(statement, parameters)
