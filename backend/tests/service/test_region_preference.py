from dataclasses import replace
from datetime import date

import pytest
from lxml import etree

from src.adapter.client.msp_registry.document import parse_document
from src.controller.uploads.csv_file import decode_notices
from src.models.enums import HighlightCode
from src.models.errors import InvalidNoticeRowError
from src.models.operations.upload import Notice
from src.models.search.search_context import SearchContext
from src.models.search.supplier_search import SupplierCandidate
from src.service.search.supplier import SupplierSearch
from src.service.supplier_search.policy.outcome import PolicyVerdict
from src.service.supplier_search.ranking.ranker import CandidateRanker
from src.service.supplier_search.settings import ScoreWeights
from tests.fakes.domain import make_supplier
from tests.fakes.drafts import make_draft


@pytest.mark.parametrize(("region", "expected"), [("78", "78"), ("", ""), ("invalid", "")])
def test_msp_reads_explicit_region_without_guessing_from_inn(region: str, expected: str) -> None:
    element = etree.fromstring(
        (
            '<Документ ДатаСост="10.09.2026"><ОргВклМСП ИННЮЛ="7707049388"/>'
            f'<СведМН КодРегион="{region}"><Регион Наим="Test"/></СведМН></Документ>'
        ).encode()
    )
    company = parse_document(element)
    assert company is not None
    assert company.region == expected
    assert company.region_name == "Test"
    assert company.registry_date == date(2026, 9, 10)


def test_region_gives_bounded_bonus_without_filtering_other_suppliers() -> None:
    ranker = CandidateRanker(ScoreWeights())
    remote = make_draft(make_supplier("remote"), fusion=0.51)
    local = make_draft(replace(make_supplier("local"), registered_region="78"), fusion=0.5)
    judged = [(remote, PolicyVerdict()), (local, PolicyVerdict())]
    neutral = ranker.rank(judged, 10)
    preferred = ranker.rank(judged, 10, "78")
    assert neutral[0].supplier.name == remote.supplier.name
    assert preferred[0].supplier.name == local.supplier.name
    assert len(preferred) == 2
    assert 0 < preferred[0].score.total.value - ranker.score(local).total.value <= 0.05
    assert any(item.code == HighlightCode.SAME_REGION for item in preferred[0].highlights)
    assert preferred[1].score == neutral[0].score
    assert ranker.rank(judged, 10, "77") == neutral


class Encoder:
    async def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        return [[1.0, 0.0]]


class Index:
    dimensions = 2
    instruction = "retrieve"

    async def search_context(
        self, text: str, vector: list[float], limit: int, context: SearchContext
    ) -> list[SupplierCandidate]:
        self.limit = limit
        return [
            SupplierCandidate("remote", "paper", "", 0.99, 0.9),
            SupplierCandidate("local", "paper", "", 0.95, 0.9, registered_region="78"),
            SupplierCandidate("unknown", "paper", "", 0.8, 0.8),
        ]

    async def search(self, text: str, vector: list[float], limit: int) -> list[SupplierCandidate]:
        return await self.search_context(text, vector, limit, SearchContext())

    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]:
        return candidates


@pytest.mark.asyncio
async def test_csv_region_reranks_wider_pool_and_keeps_unknown_region() -> None:
    index = Index()
    search = SupplierSearch(index, Encoder())
    results = await search.search_notice(Notice("1", "paper", delivery_region="78"))
    assert index.limit == 100
    assert [candidate.inn for candidate in results] == ["local", "remote", "unknown"]
    assert results[0].ranking_reasons == ["region"]
    neutral = await search.search_notice(Notice("1", "paper"))
    assert [candidate.inn for candidate in neutral] == ["remote", "local", "unknown"]
    assert not neutral[0].ranking_reasons


def test_csv_delivery_region_is_optional_and_validated() -> None:
    notice = decode_notices(b"lot_id,procedure_name,delivery_region\n1,paper,78\n")[0]
    assert notice.delivery_region == "78"
    assert decode_notices(b"lot_id,procedure_name\n1,paper\n")[0].delivery_region == ""
    with pytest.raises(InvalidNoticeRowError):
        decode_notices(b"lot_id,procedure_name,delivery_region\n1,paper,invalid\n")
