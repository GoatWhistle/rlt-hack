from collections.abc import Sequence

from src.adapter.repository.clickhouse.retrieval.prefixes import TermMatch, term_match

LOT_TEXT_COLUMN = "text"
SELECT_PARTICIPATIONS = (
    "SELECT supplier_id, lot_id, won, title, {columns} FROM {db}.supplier_lots "
    "WHERE supplier_id IN {{ids:Array(UUID)}} AND {matched} "
    "ORDER BY won DESC, lot_id DESC "
    "LIMIT {{cap:UInt32}}"
)


def participations_query(database: str, terms: Sequence[str]) -> tuple[str, TermMatch]:
    match = term_match(LOT_TEXT_COLUMN, terms)
    statement = SELECT_PARTICIPATIONS.format(
        db=database, columns=match.columns, matched=match.matched
    )
    return statement, match
