import asyncio
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import numpy as np
import pyarrow as arrow
import pyarrow.parquet as parquet

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.repository.supplier_index.index import FileSupplierIndex
from src.adapter.repository.uploads.files import FileUploads
from src.controller.search.api import app
from src.controller.uploads.csv_file import decode_notices
from src.service.errors import ServiceError
from src.service.search.supplier import SupplierSearch
from src.service.upload.worker import UploadService


class Encoder:
    async def encode(self, texts, *, query=False):
        assert not query and texts[0].startswith("Instruct: test\nQuery:")
        return [[1.0, 0.0]]


async def main():
    with TemporaryDirectory() as temporary:
        directory = Path(temporary)
        cards = [
            {"supplier_inn": "1111111111", "category": "paper", "profile_text": "office paper"},
            {"supplier_inn": "1111111111", "category": "paper", "profile_text": "white paper"},
            {"supplier_inn": "2222222222", "category": "cable", "profile_text": "copper cable"},
        ]
        parquet.write_table(arrow.Table.from_pylist(cards), directory / "cards.parquet")
        np.save(directory / "card_vectors.npy", np.array([[1, 0], [0.9, 0.1], [0, 1]], "float32"))
        (directory / "report.json").write_text("{}")
        manifest = {"shape": [3, 2], "query_instruction": "test", "files": {}}
        for name in ("cards.parquet", "card_vectors.npy", "report.json"):
            manifest["files"][name] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        (directory / "manifest.json").write_text(json.dumps(manifest))
        index = FileSupplierIndex(directory)
        await index.initialize()
        engine = SupplierSearch(index, Encoder())
        hits = await engine.search("paper", 2)
        assert len(hits) == 2 and hits[0].inn == "1111111111"
        assert len({hit.inn for hit in hits}) == 2
        for text, limit in [(" ", 1), ("x", 0), ("x" * 4001, 1)]:
            try:
                await engine.search(text, limit)
                raise AssertionError("invalid query accepted")
            except ServiceError:
                pass
        app.state.search = engine
        app.state.uploads = UploadService(engine, FileUploads(directory / "uploads"))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
            assert (await client.get("/api/health")).status_code == 200
            assert (await client.get("/api/uploads")).json() == {"uploads": []}
            response = await client.post(
                "/api/uploads",
                files={"file": ("test.csv", b"lot_id,procedure_name\ntest_1,paper\n", "text/csv")},
            )
            assert response.status_code == 200, response.text
            identifier = response.json()["id"]
            assert response.json()["processed"] == 1
            assert len((await client.get("/api/uploads")).json()["uploads"]) == 1
            response = await client.get(f"/api/uploads/{identifier}/lots/test_1")
            candidate = response.json()["recommendation"]["companies"][0]
            assert candidate["inn"] == "1111111111"
            assert candidate["status"] == "historical"
            assert candidate["history"]["examples"]
            assert candidate["similarPurchases"] is None
            assert candidate["wins"] is None
            response = await client.post(
                f"/api/uploads/{identifier}/results", json={"lotIds": ["test_1"]}
            )
            assert len(response.json()["results"]) == 1
            assert (await client.get(f"/api/uploads/{identifier}/lots/missing")).status_code == 404
            response = await client.post("/api/suppliers/search", json={"query": "paper"})
            assert response.json()["suppliers"][0]["inn"] == "1111111111"
            assert (
                await client.post("/api/suppliers/search", json={"query": ""})
            ).status_code == 422
            client.cookies.clear()
            assert (await client.get(f"/api/uploads/{identifier}")).status_code == 404
            assert (await client.get("/api/uploads")).json() == {"uploads": []}
        assert len(decode_notices("lot_id;procedure_name\nx;Бумага".encode("cp1251"))) == 1
        for data in [b"", b"title\nx", b"lot_id,procedure_name\nx,a\nx,b"]:
            try:
                decode_notices(data)
                raise AssertionError("invalid CSV accepted")
            except ValueError:
                pass
        (directory / "report.json").write_text("changed")
        try:
            await FileSupplierIndex(directory).initialize()
            raise AssertionError("corrupted index accepted")
        except ValueError:
            pass
    print("Supplier search, CSV upload, persistence and session isolation: OK")


asyncio.run(main())
