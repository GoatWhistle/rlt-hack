import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.controller.uploads.csv_file import decode_notices
from src.controller.uploads.presentation import lot_summary, summary
from src.models.operations.upload import LotRecommendation, Notice, Upload
from src.models.search.supplier_search import SupplierCandidate, SupplierPurchase
from src.service.search.supplier import SupplierSearch
from src.service.upload.evidence import relevant_evidence


class Encoder:
    async def encode(self, texts, *, query=False):
        return [[1.0, 0.0]]


class Index:
    dimensions = 2
    instruction = "retrieve"

    async def search_context(self, text, vector, limit, context):
        self.context = context
        self.text = text
        return []


async def main():
    notice = decode_notices(
        "lot_id;procedure_name;customer_inn;start_price\na;Бумага;7800000000;1 234,50".encode()
    )[0]
    assert notice.customer_inn == "7800000000" and notice.start_price == 1234.5
    assert decode_notices(b"lot_id,procedure_name\na,paper")[0] == Notice("a", "paper")
    for price in ["nan", "inf", "-1", "abc"]:
        try:
            decode_notices(f"lot_id,procedure_name,start_price\na,paper,{price}".encode())
            raise AssertionError("Invalid price accepted")
        except ValueError:
            pass
    try:
        decode_notices(b"lot_id,procedure_name,customer_inn\na,paper,1")
        raise AssertionError("Invalid customer accepted")
    except ValueError:
        pass
    index = Index()
    engine = SupplierSearch(index, Encoder())
    await engine.search_notice(notice)
    assert index.context.customer_inn == notice.customer_inn
    assert index.context.start_price == notice.start_price
    assert index.text == notice.title
    lot = LotRecommendation(notice)
    data = lot_summary(lot)
    assert data["customerInn"] == notice.customer_inn and data["startPrice"] == 1234.5
    upload = Upload("a", "b", "test.csv", "2026-10-02", [lot])
    assert summary(upload)["counts"]["failed"] == 0
    contract = json.loads(
        (Path(__file__).resolve().parents[3] / "contracts/upload/summary.example.json").read_text()
    )
    example = Upload("synthetic-upload", "owner", "test.csv", "2026-10-02T00:00:00+00:00", [lot])
    assert summary(example) == contract
    wrong = SupplierPurchase("1", "Газетная бумага", "2025-05-01", "", "archive", [], True)
    right = SupplierPurchase("2", "Бумага А4", "2025-01-01", "", "archive", ["А4"], True)
    candidate = SupplierCandidate("1", "17", "", 0.5, 0.5, purchases=[wrong, right])
    ordered = await relevant_evidence("Поставка бумаги А4", [candidate])
    assert ordered[0].purchases[0].lot_id == "2"
    assert candidate.purchases[0].lot_id == "1"
    print("CSV metadata, contextual search and upload contract: OK")


asyncio.run(main())
