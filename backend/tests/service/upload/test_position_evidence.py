from dataclasses import replace
from pathlib import Path

import pytest

from src.adapter.repository.uploads.files import FileUploads
from src.controller.uploads.presentation import result
from src.models.operations.upload import LotRecommendation, Notice, NoticePosition, Upload
from src.models.search.supplier_search import SupplierCandidate, SupplierPurchase
from src.service.normalizer.text import stems
from src.service.upload.evidence import relevant_evidence


def supplier(names: list[str], *, title: str = "Paper procurement") -> SupplierCandidate:
    return SupplierCandidate(
        "7700000000",
        "17.12",
        "profile",
        0.6,
        0.9,
        purchases=[
            SupplierPurchase("archive/1", title, "2025-02-01", "customer", "AIS", names, True)
        ],
    )


@pytest.mark.parametrize(
    ("query", "name", "matches"),
    [
        ("Бумага офисная А4 80 г/м2", "Бумага офисная А4 80 г/м2 500 листов", True),
        ("Бумага офисная А4 80 г/м2", "Бумага офисная А4 180 г/м2", False),
        ("Бумага офисная А4 80 г/м2", "Бумага офисная А3 80 г/м2", False),
        ("Вода питьевая", "Вода техническая", False),
        ("Бумага офисная", "Бумаги офисной", True),
        ("Кроссовки", "Вода питьевая", False),
        ("Paper A4 80", "Paper A4", False),
    ],
)
async def test_history_match_requires_name_and_requested_attributes(
    query: str, name: str, matches: bool
) -> None:
    position = NoticePosition("item", query, "17.12.14.110")
    candidates = await relevant_evidence(query, [supplier([name])], (position,), stems)
    assert bool(candidates[0].position_evidence) == matches


async def test_profile_title_or_category_alone_never_confirm_position() -> None:
    candidate = replace(supplier([], title="water"), profile="water", category="11.07")
    found = await relevant_evidence("water", [candidate], (NoticePosition("1", "water", "11.07"),))
    assert found[0].position_evidence == {}


async def test_duplicate_positions_keep_distinct_ids_and_unmatched_stays_unknown() -> None:
    positions = (
        NoticePosition("1", "paper"),
        NoticePosition("2", "paper"),
        NoticePosition("3", "pens"),
    )
    candidate = (await relevant_evidence("paper pens", [supplier(["paper"])], positions))[0]
    assert candidate.position_evidence == {"1": "archive/1", "2": "archive/1"}


async def test_historical_source_survives_storage_and_cannot_claim_stock(tmp_path: Path) -> None:
    notice = Notice("lot/1", "paper", positions=(NoticePosition("p1", "paper"),))
    candidate = (
        await relevant_evidence(notice.query_text, [supplier(["paper"])], notice.positions)
    )[0]
    upload = Upload(
        "a" * 32, "b" * 32, "two.csv", "2026-10-02", [LotRecommendation(notice, [candidate])]
    )
    storage = FileUploads(tmp_path)
    await storage.save(upload)
    stored = await storage.get(upload.owner, upload.upload_id)
    assert stored is not None
    company = result(stored, stored.lots[0])["recommendation"]["companies"][0]
    match = company["matches"][0]
    assert match["basis"] == "historical"
    assert match["source"]["kind"] == "purchase"
    assert match["source"]["title"] == "Paper procurement"
    assert match["source"]["checkedAt"] == "2025-02-01"
    assert match["source"]["url"].endswith("lot%2F1/evidence/7700000000/archive%2F1")
    assert "None" not in company["summary"]
    assert company["clarify"]
