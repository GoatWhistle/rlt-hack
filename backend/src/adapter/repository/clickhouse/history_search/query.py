from src.adapter.repository.clickhouse.retrieval.terms import normalized

MATCHING_LOTS = (
    "SELECT lot_id, arrayStringConcat(groupUniqArray(haystack), ' ') AS lot_text "
    "FROM ("
    "SELECT lot_id, {subject} AS haystack FROM {db}.procurement_lots_current "
    "WHERE multiSearchAny(haystack, {{needles:Array(String)}}) "
    "UNION ALL "
    "SELECT lot_id, {product} AS haystack FROM {db}.procurement_items_current "
    "WHERE multiSearchAny(haystack, {{needles:Array(String)}})"
    ") GROUP BY lot_id "
    "ORDER BY arrayCount(position -> position > 0, "
    "multiSearchAllPositions(lot_text, {{needles:Array(String)}})) DESC, lot_id "
    "LIMIT {{pool:UInt32}}"
)
PARTICIPANTS = (
    "SELECT m.lot_id, m.lot_text, p.supplier_id, max(p.is_winner) "
    "FROM ({lots}) AS m "
    "INNER JOIN {db}.lot_participations_current AS p ON p.lot_id = m.lot_id "
    "{condition}"
    "GROUP BY m.lot_id, m.lot_text, p.supplier_id"
)
REGION_CONDITION = (
    "WHERE p.supplier_id IN (SELECT supplier_id FROM {db}.suppliers_current "
    "WHERE has({{regions:Array(String)}}, region)) "
)


def participants_statement(database: str, with_regions: bool) -> str:
    lots = MATCHING_LOTS.format(
        db=database,
        subject=normalized("subject"),
        product=normalized("product_name"),
    )
    condition = REGION_CONDITION.format(db=database) if with_regions else ""
    return PARTICIPANTS.format(lots=lots, db=database, condition=condition)
