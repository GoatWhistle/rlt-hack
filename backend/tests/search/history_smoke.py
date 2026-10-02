import asyncio
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import httpx
import pyarrow as pa
import pyarrow.parquet as pq
from chdb.session import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.repository.clickhouse.engine.migrator import Migrator
from src.adapter.repository.supplier_index.history import enrich_history
from src.adapter.repository.supplier_index.history_import import import_history
from src.adapter.repository.uploads.files import FileUploads
from src.controller.search.api import app
from src.controller.uploads.presentation import result
from src.models.operations.upload import LotRecommendation, Notice, Upload
from src.models.search.supplier_search import SupplierCandidate
from src.service.upload.worker import UploadService
from tests.clickhouse.chdb_gateway import ChdbGateway


async def main():
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        database = root / "prepared.duckdb"
        with duckdb.connect(str(database)) as connection:
            connection.execute("""
                CREATE TABLE lot_info AS SELECT 'old' lot_id, 'Paper procurement' procedure_name,
                    'Paper procurement' query_text, DATE '2024-01-01' publish_date,
                    'customer' customer_inn, 'archive' source_system,
                    false notice_conflict, 1 winner_count;
                INSERT INTO lot_info SELECT 'future', 'Future secret', 'Future secret',
                    DATE '2025-01-01', 'customer', 'archive', false, 1;
                CREATE TABLE participations AS SELECT lot_id, 'supplier' supplier_inn,
                    true is_winner, false label_conflict FROM lot_info;
                CREATE TABLE lot_categories AS SELECT lot_id, '17.12' category FROM lot_info;
                CREATE TABLE products AS SELECT lot_id, '17.12' category,
                    'White paper' product_name FROM lot_info;
            """)
        pq.write_table(
            pa.Table.from_pylist([{"supplier_inn": "supplier", "category": "17.12"}]),
            root / "cards.parquet",
        )
        manifest = {
            "files": {
                "card_vectors.npy": "synthetic-index",
                "cards.parquet": hashlib.sha256((root / "cards.parquet").read_bytes()).hexdigest(),
            }
        }
        (root / "manifest.json").write_text(json.dumps(manifest))
        session = Session(str(root / "ch"))
        try:
            gateway = ChdbGateway(session)
            await Migrator(gateway).apply_pending()
            candidate = SupplierCandidate("supplier", "17.12", "Paper", 0.1, 0.8)
            before = await enrich_history(
                gateway, "supplier_search", "synthetic-index", [candidate]
            )
            assert not before[0].purchases
            report = await import_history(gateway, "supplier_search", database, root)
            assert report == {"rows": 1, "already_present": False}
            assert (await import_history(gateway, "supplier_search", database, root))[
                "already_present"
            ]
            enriched = (
                await enrich_history(gateway, "supplier_search", "synthetic-index", [candidate])
            )[0]
            assert enriched.category_lots == enriched.category_wins == 1
            assert enriched.purchases[0].lot_id == "old"
            assert enriched.purchases[0].product_names == ["White paper"]
            assert enriched.purchases[0].is_winner
            upload = Upload(
                "a" * 32,
                "b" * 32,
                "test.csv",
                "2026-10-02",
                [LotRecommendation(Notice("lot", "Paper"), [enriched])],
            )
            repository = FileUploads(root / "uploads")
            await repository.save(upload)
            assert (await repository.get(upload.owner, upload.upload_id)) == upload
            company = result(upload, upload.lots[0])["recommendation"]["companies"][0]
            assert company["status"] == "recommended"
            assert company["similarPurchases"] == 1
            source = "/api" + company["purchases"][0]["source"]["url"]
            app.state.uploads = UploadService(object(), repository)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="https://test",
                cookies={"rlt_session": upload.owner},
            ) as client:
                response = await client.get(source)
                assert response.status_code == 200 and response.json()["lot_id"] == "old"
                assert response.json()["provenance"] == "procurement_archive"
                assert (await client.get(source.replace("/old", "/future"))).status_code == 404
                client.cookies.clear()
                assert (await client.get(source)).status_code == 404
            print("Historical evidence: temporal cutoff, import, retry and source facts OK")
        finally:
            session.close()


asyncio.run(main())
