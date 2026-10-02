from collections.abc import Sequence

from src.adapter.repository.clickhouse.retrieval.prefixes import TermMatch, term_match

LOT_TEXT_COLUMN = "text"
PARTICIPANTS = (
    "SELECT m.lot_id, m.terms, supplier_id, has(m.winners, supplier_id), m.flags FROM ("
    "SELECT lot_id, terms, participants, winners, {columns} FROM {db}.lot_texts "
    "WHERE {matched} ORDER BY {hits} DESC, lot_id LIMIT {{pool:UInt32}}"
    ") AS m ARRAY JOIN m.participants AS supplier_id {condition}"
)
REGION_CONDITION = (
    "WHERE supplier_id IN (SELECT supplier_id FROM {db}.suppliers_current "
    "WHERE has({{regions:Array(String)}}, region))"
)


def participants_query(
    database: str, terms: Sequence[str], with_regions: bool
) -> tuple[str, TermMatch]:
    match = term_match(LOT_TEXT_COLUMN, terms)
    condition = REGION_CONDITION.format(db=database) if with_regions else ""
    statement = PARTICIPANTS.format(
        db=database,
        columns=match.columns,
        matched=match.matched,
        hits=match.hits,
        condition=condition,
    )
    return statement, match
