import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import numpy as np
import pyarrow as arrow
from chdb.session import Session
from pyarrow import parquet

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.repository.clickhouse.catalog.offer import ClickHouseOfferRepository
from src.adapter.repository.clickhouse.catalog.supplier import ClickHouseSupplierRepository
from src.adapter.repository.clickhouse.engine.migrator import Migrator
from src.adapter.repository.clickhouse.engine.versions import VersionSequencer
from src.adapter.repository.supplier_index.clickhouse import ClickHouseSupplierIndex
from src.adapter.repository.supplier_index.importer import import_index
from src.models.catalog.offer import Offer
from src.models.catalog.supplier import Supplier
from tests.clickhouse.chdb_gateway import ChdbGateway


async def main():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        directory = root / "index"
        directory.mkdir()
        cards = [
            {
                "card_id": "a",
                "supplier_inn": "1111111111",
                "category": "paper",
                "profile_text": "office paper",
            },
            {
                "card_id": "b",
                "supplier_inn": "1111111111",
                "category": "paper",
                "profile_text": "white paper",
            },
            {
                "card_id": "c",
                "supplier_inn": "2222222222",
                "category": "cable",
                "profile_text": "copper cable",
            },
        ]
        parquet.write_table(arrow.Table.from_pylist(cards), directory / "cards.parquet")
        np.save(directory / "card_vectors.npy", np.array([[1, 0], [0.9, 0.1], [0, 1]], "float32"))
        (directory / "report.json").write_text("{}")
        manifest = {
            "shape": [3, 2],
            "model": "synthetic",
            "revision": "1",
            "history_before": "2025-01-01",
            "query_instruction": "test",
            "files": {},
        }
        for name in ("cards.parquet", "card_vectors.npy", "report.json"):
            manifest["files"][name] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        (directory / "manifest.json").write_text(json.dumps(manifest))
        session = Session(str(root / "db"))
        try:
            gateway = ChdbGateway(session)
            await Migrator(gateway).apply_pending()
            first = await import_index(gateway, "supplier_search", directory)
            assert first["cards"] == 3 and first["already_present"] == 0
            second = await import_index(gateway, "supplier_search", directory)
            assert second["already_present"] == 3
            index = ClickHouseSupplierIndex(
                directory, gateway, first["index_id"], "supplier_search"
            )
            await index.initialize()
            versions = VersionSequencer()
            supplier = Supplier(
                uuid4(),
                "Synthetic Paper",
                inn="1111111111",
                website="https://example.test",
                contacts={"email": "a@example.test"},
                identity_evidence_url="https://example.test/company",
            )
            await ClickHouseSupplierRepository(gateway, versions).save_many([supplier])
            now = datetime.now(UTC)
            await ClickHouseOfferRepository(gateway, versions).save_many(
                [
                    Offer(
                        uuid4(),
                        uuid4(),
                        "paper",
                        "https://example.test/paper",
                        "Office paper",
                        now,
                        now,
                        supplier_id=supplier.supplier_id,
                    )
                ],
                now,
            )
            hits = await index.search("paper", [1.0, 0.0], 2)
            assert hits[0].inn == "1111111111" and len(hits) == 2
            assert hits[0].similarity > 0.99
            assert not hasattr(index, "vectors")
            assert hits[0].name == "Synthetic Paper"
            assert hits[0].email == "a@example.test"
            assert hits[0].history_examples
            assert hits[0].catalog[0].name == "Office paper"
            assert hits[1].name == "" and hits[1].catalog == []
            await gateway.insert(
                "supplier_search.msp_companies",
                ("inn", "name", "registry_date"),
                [
                    ("1111111111", "Registry Paper", now.date()),
                    ("2222222222", "Synthetic Cable", now.date()),
                ],
            )
            enriched = await index.enrich(hits)
            assert enriched[0].name == "Synthetic Paper"
            assert enriched[1].name == "Synthetic Cable"
            assert enriched[1].website == "" and enriched[1].identity_url == ""
            print("ClickHouse import, repeat import, dimensions, supplier grouping and search: OK")
        finally:
            session.close()


asyncio.run(main())
