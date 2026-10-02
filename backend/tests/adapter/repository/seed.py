from collections.abc import Sequence
from datetime import date, datetime
from uuid import UUID

from src.adapter.repository.clickhouse.offer import ClickHouseOfferRepository
from src.adapter.repository.clickhouse.protocols import SqlGateway
from src.adapter.repository.clickhouse.source import ClickHouseSourceRepository
from src.adapter.repository.clickhouse.supplier import ClickHouseSupplierRepository
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.models.offer import Offer
from src.models.source import Source
from src.models.supplier import Supplier
from tests.fakes.domain import CHECKED, uid

DATABASE = "supplier_search"
MATCH_COLUMNS = (
    "offer_id",
    "catalog_item_id",
    "status",
    "confidence",
    "offer_content_hash",
    "version",
)

EVIDENCE_COLUMNS = (
    "index_id",
    "supplier_inn",
    "category",
    "lot_id",
    "title",
    "publish_date",
    "customer_inn",
    "source_system",
    "product_names",
    "is_winner",
    "category_lots",
    "category_wins",
)


class Seeder:
    def __init__(self, gateway: SqlGateway) -> None:
        self._gateway = gateway
        versions = VersionSequencer()
        self._suppliers = ClickHouseSupplierRepository(gateway, versions)
        self._sources = ClickHouseSourceRepository(gateway, versions)
        self._offers = ClickHouseOfferRepository(gateway, versions)

    async def suppliers(self, *suppliers: Supplier) -> None:
        await self._suppliers.save_many(suppliers)

    async def sources(self, *sources: Source) -> None:
        await self._sources.save_many(sources)

    async def offers(self, *offers: Offer, updated_at: datetime = CHECKED) -> None:
        await self._offers.save_many(offers, updated_at)

    async def match(self, offer_id: UUID, status: str, content_hash: str = "") -> None:
        await self._gateway.insert(
            f"{DATABASE}.offer_matches",
            (
                "offer_id",
                "catalog_item_id",
                "status",
                "confidence",
                "offer_content_hash",
                "version",
            ),
            [(offer_id, offer_id, status, 0.9, content_hash, 1)],
        )

    async def lot(self, lot_id: str, subject: str, products: Sequence[str] = ()) -> None:
        await self._gateway.insert(
            f"{DATABASE}.procurement_lots",
            ("lot_id", "procedure_id", "reqnum", "procedure_name", "subject", "version"),
            [(lot_id, lot_id, lot_id, "Закупка", subject, 1)],
        )
        await self._gateway.insert(
            f"{DATABASE}.procurement_items",
            ("procurement_item_id", "lot_id", "product_name", "version"),
            [
                (uid(f"item:{lot_id}:{index}"), lot_id, name, 1)
                for index, name in enumerate(products)
            ],
        )

    async def participation(self, lot_id: str, supplier: Supplier, won: bool) -> None:
        await self._gateway.insert(
            f"{DATABASE}.lot_participations",
            ("lot_id", "supplier_inn", "supplier_kpp", "supplier_id", "is_winner", "version"),
            [(lot_id, supplier.inn or "", "", supplier.supplier_id, int(won), 1)],
        )

    async def evidence(
        self,
        supplier: Supplier,
        lot_id: str,
        title: str,
        *,
        category: str = "10.61",
        won: bool = False,
        category_lots: int = 1,
        category_wins: int = 0,
        index_id: str = "index-1",
    ) -> None:
        tail = ("7807022750", "ЕИС", [title], int(won), category_lots, category_wins)
        await self._gateway.insert(
            f"{DATABASE}.supplier_procurement_evidence",
            EVIDENCE_COLUMNS,
            [(index_id, supplier.inn or "", category, lot_id, title, date(2024, 11, 6), *tail)],
        )

    async def evidence_import(self, index_id: str = "index-1", rows: int = 1) -> None:
        await self._gateway.insert(
            f"{DATABASE}.supplier_evidence_imports",
            ("index_id", "history_before", "row_count", "prepared_sha256"),
            [(index_id, date(2025, 6, 1), rows, "sha")],
        )
