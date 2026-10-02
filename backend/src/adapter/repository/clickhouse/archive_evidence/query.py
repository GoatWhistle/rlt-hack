from src.adapter.repository.clickhouse.retrieval.terms import normalized

SELECT_EVIDENCE = (
    "SELECT s.supplier_id, e.category, e.lot_id, e.title, e.is_winner, "
    "e.category_lots, e.category_wins, arrayStringConcat(e.product_names, ' ') AS products "
    "FROM {db}.supplier_procurement_evidence AS e FINAL "
    "INNER JOIN (SELECT supplier_id, ifNull(inn, '') AS inn FROM {db}.suppliers_current "
    "WHERE supplier_id IN {{ids:Array(UUID)}}) AS s ON s.inn = e.supplier_inn "
    "WHERE e.index_id = (SELECT argMax(index_id, imported_at) "
    "FROM {db}.supplier_evidence_imports) "
    "AND multiSearchAny({haystack}, {{needles:Array(String)}}) "
    "ORDER BY e.is_winner DESC, e.publish_date DESC, e.lot_id "
    "LIMIT {{cap:UInt32}}"
)


def evidence_statement(database: str) -> str:
    haystack = normalized("concat(e.title, ' ', products)")
    return SELECT_EVIDENCE.format(db=database, haystack=haystack)
