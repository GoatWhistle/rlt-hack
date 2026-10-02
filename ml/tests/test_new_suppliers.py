from pathlib import Path

from rlt_ml.new_suppliers import aggregate, sheet_rows, write_sheet

QUERIES = [
    {"id": "q1", "category": "paper", "text": "Бумага А4"},
    {"id": "q2", "category": "food", "text": "Крупа"},
]


def answer(text: str) -> dict:
    if text == "Крупа":
        return {"candidates": [{"rank": 1, "inn": "1", "name": "Old", "novelty": "known",
                                "status": "check", "matches": []}]}
    offer = {"name": "Бумага SvetoCopy A4", "url": "https://x.ru/1", "observedAt": "2026-09-29"}
    return {"candidates": [
        {"rank": rank, "inn": str(rank), "name": f"N{rank}", "novelty": "new",
         "status": "recommended" if rank == 1 else "check",
         "matches": [{"offer": offer}]}
        for rank in range(1, 8)
    ]}


def test_sheet_keeps_queries_without_new_candidates_and_caps_five(tmp_path: Path) -> None:
    rows = sheet_rows(QUERIES, answer)
    assert len([row for row in rows if row["query_id"] == "q1"]) == 5
    assert [row["rationale"] for row in rows if row["query_id"] == "q2"] == ["no new candidates"]
    write_sheet(tmp_path / "sheet.csv", rows)
    assert (tmp_path / "sheet.csv").read_text(encoding="utf-8").startswith("query_id,category")


def test_aggregate_counts_false_confirmations_and_unknown_fields() -> None:
    rows = sheet_rows(QUERIES, answer)
    for row in rows:
        if row.get("rank") == 1:
            row.update(label="does_not_fit", link_ok="yes", reviewer="a")
        elif row.get("rank"):
            row.update(label="fits", link_ok="no", product_ok="unknown", reviewer="a")
    summary = aggregate(rows)
    assert (summary["queries"], summary["categories"], summary["candidates"]) == (2, 2, 5)
    assert summary["queries_with_suitable_new"] == 0.5
    assert summary["false_confirmations"] == 0.2
    assert summary["broken_evidence"] == 0.8
    assert summary["unknown_fields"] == 0.8
    assert summary["reviewers"] == 1
