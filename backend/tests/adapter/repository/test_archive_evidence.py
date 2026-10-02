import pytest

from src.adapter.repository.clickhouse.archive_evidence.combined import CombinedPurchaseHistory
from src.adapter.repository.clickhouse.archive_evidence.history import ClickHouseArchiveEvidence
from src.adapter.repository.clickhouse.archive_evidence.purchases import (
    ClickHouseArchivePurchases,
)
from src.adapter.repository.clickhouse.participation.history import ClickHousePurchaseHistory
from src.adapter.text.analyzer.analyzer import RussianAnalyzer
from src.models.enums import PurchaseOutcome
from tests.adapter.repository.seed import Seeder
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.fakes.domain import make_item, make_supplier

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb

ALPHA = make_supplier("alpha", inn="7801234564")
BETA = make_supplier("beta", inn="7707083893")
ITEMS = (make_item("i1", "Крупа гречневая"), make_item("i2", "Бумага офисная"))


async def seeded(gateway: ChdbGateway) -> Seeder:
    seeder = Seeder(gateway)
    await seeder.suppliers(ALPHA, BETA)
    await seeder.evidence(
        ALPHA, "L1", "Поставка крупы гречневой", won=True, category_lots=9, category_wins=4
    )
    await seeder.evidence(
        ALPHA, "L2", "Крупа гречневая ядрица для школ", category_lots=9, category_wins=4
    )
    await seeder.evidence(BETA, "L3", "Канцелярия и бумага офисная", category="17.12")
    await seeder.evidence(BETA, "L9", "Крупа гречневая", index_id="index-0")
    await seeder.evidence_import()
    return seeder


async def test_archive_history_matches_items_within_the_active_snapshot(
    gateway: ChdbGateway,
) -> None:
    await seeded(gateway)
    history = ClickHouseArchiveEvidence(gateway, RussianAnalyzer())
    found = await history.summarize([ALPHA.supplier_id, BETA.supplier_id], ITEMS, 5)
    alpha = found[ALPHA.supplier_id]
    assert (alpha.similar, alpha.wins) == (9, 4)
    assert [record.lot_id for record in alpha.records] == ["L1", "L2"]
    assert alpha.records[0].outcome == PurchaseOutcome.WINNER
    assert alpha.records[0].item_ids == ("i1",)
    beta = found[BETA.supplier_id]
    assert [record.lot_id for record in beta.records] == ["L3"]
    assert beta.records[0].item_ids == ("i2",)
    assert await history.summarize([], ITEMS, 5) == {}


async def test_combined_history_prefers_the_richer_source(gateway: ChdbGateway) -> None:
    seeder = await seeded(gateway)
    await seeder.lot("P1", "Крупа гречневая", ("Крупа гречневая",))
    await seeder.participation("P1", ALPHA, won=False)
    analyzer = RussianAnalyzer()
    combined = CombinedPurchaseHistory(
        ClickHousePurchaseHistory(gateway, analyzer),
        ClickHouseArchiveEvidence(gateway, analyzer),
    )
    found = await combined.summarize([ALPHA.supplier_id], ITEMS, 5)
    assert found[ALPHA.supplier_id].similar == 9


async def test_archive_record_is_read_for_its_supplier_only(gateway: ChdbGateway) -> None:
    await seeded(gateway)
    purchases = ClickHouseArchivePurchases(gateway)
    record = await purchases.get(ALPHA.supplier_id, "L1")
    assert record is not None
    assert (record.title, record.outcome, record.customer_inn) == (
        "Поставка крупы гречневой",
        PurchaseOutcome.WINNER,
        "7807022750",
    )
    assert record.published.isoformat() == "2024-11-06"
    assert record.snapshot == "index-1"
    assert await purchases.get(BETA.supplier_id, "L1") is None
    assert await purchases.get(BETA.supplier_id, "L9") is None
