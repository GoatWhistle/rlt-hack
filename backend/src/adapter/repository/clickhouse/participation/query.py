from src.adapter.repository.clickhouse.retrieval.terms import normalized

SELECT_PARTICIPATIONS = (
    "SELECT p.supplier_id, p.lot_id, max(p.is_winner) AS won, "
    "any(l.subject) AS lot_subject, any(l.procedure_name) AS lot_procedure, "
    "arrayStringConcat(groupUniqArray(50)(i.product_name), ' ') AS lot_products "
    "FROM {db}.lot_participations_current AS p "
    "LEFT JOIN {db}.procurement_lots_current AS l ON l.lot_id = p.lot_id "
    "LEFT JOIN {db}.procurement_items_current AS i ON i.lot_id = p.lot_id "
    "WHERE p.supplier_id IN {{ids:Array(UUID)}} "
    "GROUP BY p.supplier_id, p.lot_id "
    "HAVING multiSearchAny({haystack}, {{needles:Array(String)}}) "
    "ORDER BY won DESC, p.lot_id DESC "
    "LIMIT {{cap:UInt32}}"
)


def participations_statement(database: str) -> str:
    haystack = normalized("concat(lot_subject, ' ', lot_procedure, ' ', lot_products)")
    return SELECT_PARTICIPATIONS.format(db=database, haystack=haystack)
