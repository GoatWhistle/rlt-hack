from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from src.adapter.repository.supplier_index import index as index_module
from src.adapter.repository.supplier_index.category_priority import (
    requested_categories,
    supplier_category_coverage,
)
from src.adapter.repository.supplier_index.index import FileSupplierIndex
from src.models.operations.upload import Notice, NoticePosition
from src.models.search.search_context import SearchContext
from src.models.search.supplier_search import SupplierCandidate
from src.service.search.supplier import SupplierSearch


def test_category_is_explicit_and_full_code_is_not_invented() -> None:
    context = SearchContext(
        okpd2_codes=("17.12.14.110", "17.12.13", "bad", "01", "17.12.bad", "17.12.")
    )
    assert requested_categories(context) == {"17.12"}
    cards = [
        {"supplier_inn": "multi", "category": "17.12"},
        {"supplier_inn": "multi", "category": "17.12"},
        {"supplier_inn": "multi", "category": "28.13"},
        {"supplier_inn": "other", "category": "01.11"},
    ]
    assert supplier_category_coverage(cards, frozenset({"17.12", "28.13"})) == {"multi": 2}
    assert requested_categories(None) == set()


def test_category_retrieval_keeps_low_semantic_match_and_other_companies(tmp_path: Path) -> None:
    index = cast(Any, FileSupplierIndex(tmp_path))
    index.cards = [
        {"supplier_inn": "wrong", "category": "01.11", "profile_text": "paper"},
        {"supplier_inn": "right", "category": "17.12", "profile_text": "paper"},
    ]
    index.vectorizer = cast(Any, index_module).CountVectorizer()
    index.lexical = index.vectorizer.fit_transform(["paper paper", "paper"])
    index._metadata = lambda candidate: candidate
    candidates = index._fuse(
        "paper", np.asarray([0.99, 0.1]), 2, SearchContext(okpd2_codes=("17.12.14",))
    )
    assert [candidate.inn for candidate in candidates] == ["right", "wrong"]
    assert candidates[0].matched_category_count == 1
    assert candidates[1].matched_category_count == 0
    neutral = index._fuse("paper", np.asarray([0.99, 0.1]), 2)
    assert neutral[0].inn == "wrong"


class Encoder:
    async def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        return [[1.0, 0.0]]


class Index:
    instruction = "retrieve"
    dimensions = 2

    async def search_context(
        self, text: str, vector: list[float], limit: int, context: SearchContext
    ) -> list[SupplierCandidate]:
        self.context = context
        return [
            SupplierCandidate("right", "17.12", "", 0.8, 0.8, matched_category_count=1),
            SupplierCandidate("local-wrong", "01.11", "", 0.99, 0.9, registered_region="78"),
        ]

    async def search(self, text: str, vector: list[float], limit: int) -> list[SupplierCandidate]:
        return []

    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]:
        return candidates


@pytest.mark.asyncio
async def test_notice_passes_item_codes_and_region_does_not_override_category() -> None:
    index = Index()
    notice = Notice(
        "1",
        "paper",
        delivery_region="78",
        positions=(NoticePosition("1", "paper", "17.12.14.110"),),
    )
    result = await SupplierSearch(index, Encoder()).search_notice(notice)
    assert index.context.okpd2_codes == ("17.12.14.110",)
    assert [candidate.inn for candidate in result] == ["right", "local-wrong"]


def test_category_retrieval_adds_profiles_beyond_rrf_pool(tmp_path: Path) -> None:
    index = cast(Any, FileSupplierIndex(tmp_path))
    index.cards = [
        {"supplier_inn": f"wrong-{number:03}", "category": "01.11", "profile_text": "paper"}
        for number in range(301)
    ] + [
        {"supplier_inn": "right-weak", "category": "17.12", "profile_text": "paper"},
        {"supplier_inn": "right-strong", "category": "17.12", "profile_text": "paper"},
    ]
    index.vectorizer = cast(Any, index_module).CountVectorizer()
    index.lexical = index.vectorizer.fit_transform(["unrelated"] * 303)
    index._metadata = lambda candidate: candidate
    candidates = index._fuse(
        "paper",
        np.asarray([1.0] * 301 + [0.1, 0.2]),
        3,
        SearchContext(okpd2_codes=("17.12.14",)),
    )
    assert [candidate.inn for candidate in candidates[:2]] == ["right-strong", "right-weak"]
    assert candidates[2].matched_category_count == 0
