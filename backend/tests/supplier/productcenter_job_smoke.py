"""ProductCenter: повторный и оборванный обход на временной базе chDB."""

import asyncio
import sys
import tempfile
from pathlib import Path

from chdb.session import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.clock import SystemClock
from src.adapter.repository.clickhouse.journal import ClickHouseJournalRepository
from src.adapter.repository.clickhouse.migrator import MIGRATION_DIR, Migrator
from src.adapter.repository.clickhouse.offer import ClickHouseOfferRepository
from src.adapter.repository.clickhouse.package import ClickHousePackageRepository
from src.adapter.repository.clickhouse.source import ClickHouseSourceRepository
from src.adapter.repository.clickhouse.supplier import ClickHouseSupplierRepository
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.models.enums import FetchStatus
from src.service.supplier.worker import SupplierSyncWorker
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.supplier.productcenter_smoke import G1, pages, provider


async def check() -> None:
    with tempfile.TemporaryDirectory(prefix="rlt-productcenter-") as directory:
        session = Session(str(Path(directory) / "db"))
        try:
            gateway = ChdbGateway(session)
            await Migrator(gateway, MIGRATION_DIR).apply_pending()
            versions = VersionSequencer()
            journal = ClickHouseJournalRepository(gateway)
            storage = ClickHousePackageRepository(
                sources=ClickHouseSourceRepository(gateway, versions),
                suppliers=ClickHouseSupplierRepository(gateway, versions),
                offers=ClickHouseOfferRepository(gateway, versions),
                batch_size=10,
            )
            data = pages()

            async def sync(snapshot: dict[str, bytes]):
                adapter = provider(snapshot)
                worker = SupplierSyncWorker(
                    providers=[adapter],
                    storage=storage,
                    journal=journal,
                    clock=SystemClock(),
                )
                return await worker.run_once(), adapter.source.source_id

            first, source_id = await sync(data)
            assert first.failed == 0
            rows = await gateway.select(
                "SELECT external_id, first_seen_at FROM supplier_search.offers_current "
                "ORDER BY external_id"
            )
            assert [row[0] for row in rows] == ["21", "22"], rows
            first_seen = {row[0]: row[1] for row in rows}

            second, _ = await sync(data)
            assert second.failed == 0
            assert second.sources[0].offers_withdrawn == 0
            supplier_count = await gateway.select(
                "SELECT count() FROM supplier_search.suppliers_current"
            )
            assert supplier_count[0][0] == 3
            repeated = await gateway.select(
                "SELECT external_id, first_seen_at FROM supplier_search.offers_current "
                "ORDER BY external_id"
            )
            assert len(repeated) == 2
            assert {row[0]: row[1] for row in repeated} == first_seen

            broken = data.copy()
            del broken[G1]
            third, _ = await sync(broken)
            assert third.failed == 1
            remaining = await gateway.select(
                "SELECT external_id, availability FROM supplier_search.offers_current "
                "ORDER BY external_id"
            )
            assert remaining == [("21", "available"), ("22", "available")], remaining
            runs = await journal.last_runs(source_id)
            assert [run.status for run in runs] == [
                FetchStatus.FAILED,
                FetchStatus.SUCCESS,
                FetchStatus.SUCCESS,
            ]
        finally:
            session.close()
    print("ProductCenter: repeated storage and failed crawl OK")


if __name__ == "__main__":
    asyncio.run(check())
