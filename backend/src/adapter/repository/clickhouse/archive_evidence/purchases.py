from datetime import date
from uuid import UUID

from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.models.archive_purchase import ArchivePurchase
from src.models.enums import PurchaseOutcome

SELECT_PURCHASE = (
    "SELECT e.supplier_inn, e.lot_id, e.title, e.publish_date, e.is_winner, e.category, "
    "e.customer_inn, e.source_system, e.product_names, e.index_id "
    "FROM {db}.supplier_procurement_evidence AS e FINAL "
    "WHERE e.supplier_inn = (SELECT ifNull(inn, '') FROM {db}.suppliers_current "
    "WHERE supplier_id = {{supplier:UUID}} LIMIT 1) "
    "AND e.lot_id = {{lot:String}} "
    "AND e.index_id = (SELECT argMax(index_id, imported_at) "
    "FROM {db}.supplier_evidence_imports) "
    "ORDER BY e.is_winner DESC LIMIT 1"
)


class ClickHouseArchivePurchases:
    def __init__(self, gateway: SqlGateway, database: str = "supplier_search") -> None:
        self._gateway = gateway
        self._db = database

    async def get(self, supplier_id: UUID, lot_id: str) -> ArchivePurchase | None:
        rows = await self._gateway.select(
            SELECT_PURCHASE.format(db=self._db), {"supplier": str(supplier_id), "lot": lot_id}
        )
        if not rows:
            return None
        row = rows[0]
        published = row[3] if isinstance(row[3], date) else date.fromisoformat(str(row[3])[:10])
        return ArchivePurchase(
            supplier_inn=str(row[0]),
            lot_id=str(row[1]),
            title=str(row[2] or row[1]),
            published=published,
            outcome=PurchaseOutcome.WINNER if int(str(row[4])) else PurchaseOutcome.PARTICIPANT,
            category=str(row[5] or ""),
            customer_inn=str(row[6] or ""),
            source_system=str(row[7] or ""),
            products=tuple(str(name) for name in (row[8] or ())),
            snapshot=str(row[9] or ""),
        )
