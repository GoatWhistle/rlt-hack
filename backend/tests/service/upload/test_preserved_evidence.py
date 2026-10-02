from dataclasses import replace

import httpx
import pytest
from fastapi import FastAPI

from src.controller.uploads.api import router
from src.models.search.supplier_search import SupplierCandidate, SupplierPurchase
from src.service.upload.worker import UploadService
from tests.service.upload.test_worker import MemoryUploads


class Search:
    version = "archive-snapshot/query-aware-v1"

    def __init__(self, has_evidence: bool) -> None:
        self.candidate = SupplierCandidate(
            "7700000000",
            "17.12",
            "profile",
            0.5,
            0.9,
            purchases=[
                SupplierPurchase(
                    "relevant",
                    "Office paper",
                    "2024-01-01",
                    "customer",
                    "EM",
                    ["Paper A4"],
                    True,
                )
            ]
            if has_evidence
            else [],
        )
        self.metadata_refreshes = 0

    async def search(self, text: str, limit: int = 10) -> list[SupplierCandidate]:
        return [self.candidate]

    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]:
        self.metadata_refreshes += 1
        return [
            replace(
                candidate,
                name="Updated actual name",
                category_lots=42,
                purchases=[
                    SupplierPurchase(
                        "static-fallback",
                        "Shoes",
                        "2024-12-01",
                        "",
                        "EM",
                        ["Shoes"],
                        True,
                    )
                ],
            )
            for candidate in candidates
        ]


async def create_upload(http: httpx.AsyncClient) -> str:
    created = await http.post(
        "/api/uploads",
        files={
            "file": ("notices.csv", b"lot_id;procedure_name\nlot;Paper A4\n", "text/csv"),
            "items_file": (
                "items.csv",
                b"lot_id;product_name;okpd2_code\nlot;Paper A4;17.12.14.110\n",
                "text/csv",
            ),
        },
    )
    assert created.status_code == 200
    return str(created.json()["id"])


@pytest.mark.parametrize("has_evidence", [False, True])
async def test_post_reopen_and_evidence_keep_query_snapshot(has_evidence: bool) -> None:
    search = Search(has_evidence)
    repository = MemoryUploads()
    application = FastAPI()
    application.state.uploads = UploadService(search, repository)
    application.include_router(router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application),
        base_url="http://test",
    ) as http:
        upload_id = await create_upload(http)
        prefix = f"/api/uploads/{upload_id}/lots/lot"
        for _ in range(2):
            reopened = await http.get(prefix)
            assert reopened.status_code == 200
            company = reopened.json()["recommendation"]["companies"][0]
            assert company["name"] == "Updated actual name"
            assert len(company["purchases"]) == int(has_evidence)
            assert len(company["matches"]) == int(has_evidence)
            if has_evidence:
                source = company["purchases"][0]["source"]["url"]
                proof = await http.get("/api" + source)
                assert proof.status_code == 200
                assert proof.json()["lot_id"] == "relevant"
                assert proof.json()["product_names"] == ["Paper A4"]
        unrelated = await http.get(prefix + "/evidence/7700000000/static-fallback")
        assert unrelated.status_code == 404
        assert search.metadata_refreshes >= 3
        stored = repository.saved[upload_id].lots[0].candidates[0]
        assert stored.purchases == search.candidate.purchases
