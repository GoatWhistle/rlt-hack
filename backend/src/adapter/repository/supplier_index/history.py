from dataclasses import replace

from src.adapter.repository.supplier_index.protocols import SqlGateway
from src.models.supplier_search import SupplierCandidate, SupplierPurchase


async def enrich_history(
    gateway: SqlGateway,
    database: str,
    index_id: str,
    candidates: list[SupplierCandidate],
) -> list[SupplierCandidate]:
    rows = await gateway.select(
        "SELECT supplier_inn, category, lot_id, title, toString(publish_date), "
        "customer_inn, source_system, product_names, is_winner, category_lots, category_wins "
        f"FROM {database}.supplier_procurement_evidence FINAL "
        "WHERE index_id={index:String} AND supplier_inn IN {inns:Array(String)} "
        f"AND index_id IN (SELECT index_id FROM {database}.supplier_evidence_imports FINAL) "
        "ORDER BY is_winner DESC, publish_date DESC, lot_id",
        {"index": index_id, "inns": list({item.inn for item in candidates})},
    )
    purchases: dict[tuple[str, str], list[SupplierPurchase]] = {}
    counts: dict[tuple[str, str], tuple[int, int]] = {}
    for (
        inn,
        category,
        lot,
        title,
        published,
        customer,
        system,
        products,
        winner,
        lots,
        wins,
    ) in rows:
        key = (inn, category)
        purchases.setdefault(key, []).append(
            SupplierPurchase(lot, title, published, customer, system, products, bool(winner))
        )
        counts[key] = (lots, wins)
    result = []
    for candidate in candidates:
        key = (candidate.inn, candidate.category)
        lots, wins = counts.get(key, (None, None))
        result.append(
            replace(
                candidate, purchases=purchases.get(key, []), category_lots=lots, category_wins=wins
            )
        )
    return result
