from decimal import Decimal

import pytest

from src.models.operations.upload import Notice, NoticePosition
from src.models.search.search_context import SearchContext
from src.models.search.supplier_search import SupplierCandidate
from src.service.errors import ServiceError
from src.service.search.supplier import SupplierSearch


class RecordingEncoder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.invalid: list[list[float]] | None = None
        self.fail_call: int | None = None

    async def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        assert query is False
        self.calls.append(texts)
        if len(self.calls) == self.fail_call:
            raise RuntimeError("embedding unavailable")
        if self.invalid is not None:
            return self.invalid
        return [[1.0, 0.0] for _ in texts]


class RecordingIndex:
    dimensions = 2
    instruction = "retrieve relevant suppliers"
    version = "synthetic-snapshot"

    def __init__(self) -> None:
        self.calls: list[tuple[str, SearchContext, int]] = []

    async def search_context(
        self, text: str, vector: list[float], limit: int, context: SearchContext
    ) -> list[SupplierCandidate]:
        self.calls.append((text, context, limit))
        return [SupplierCandidate("7700000000", "17.12", text, 0.5, 0.9)]

    async def search(self, text: str, vector: list[float], limit: int) -> list[SupplierCandidate]:
        return await self.search_context(text, vector, limit, SearchContext())

    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]:
        return candidates


def notices(count: int) -> list[Notice]:
    return [
        Notice(
            f"lot-{index}",
            f"Purchase {index}",
            "office supplies",
            "7801234564",
            Decimal(index + 1),
            "78" if index % 2 else "",
            (
                NoticePosition(f"paper-{index}", "Paper A4", "17.12.14.110"),
                NoticePosition(f"pens-{index}", "Pens", "32.99.12.110"),
            ),
        )
        for index in range(count)
    ]


async def test_38_notices_use_three_embedding_batches_and_preserve_context() -> None:
    encoder = RecordingEncoder()
    index = RecordingIndex()
    search = SupplierSearch(index, encoder)
    inputs = notices(38)
    results = await search.search_notices(inputs, 7)
    assert [len(batch) for batch in encoder.calls] == [16, 16, 6]
    assert len(results) == 38
    for notice, (text, context, limit), result in zip(inputs, index.calls, results, strict=True):
        assert text == notice.query_text
        assert context == SearchContext(
            notice.customer_inn,
            notice.start_price,
            notice.delivery_region,
            ("17.12.14.110", "32.99.12.110"),
        )
        assert limit == (100 if notice.delivery_region else 7)
        assert result[0].profile == notice.query_text
    assert search.version == "synthetic-snapshot/region-v1/okpd2-v1"


async def test_single_notice_and_batch_have_identical_results() -> None:
    search = SupplierSearch(RecordingIndex(), RecordingEncoder())
    inputs = notices(3)
    together = await search.search_notices(inputs)
    individually = [await search.search_notice(notice) for notice in inputs]
    assert together == individually


async def test_empty_batch_does_not_call_encoder() -> None:
    encoder = RecordingEncoder()
    assert await SupplierSearch(RecordingIndex(), encoder).search_notices([]) == []
    assert encoder.calls == []


@pytest.mark.parametrize("limit", [0, 101])
async def test_bad_limit_fails_before_embedding(limit: int) -> None:
    encoder = RecordingEncoder()
    with pytest.raises(ServiceError, match="лимит"):
        await SupplierSearch(RecordingIndex(), encoder).search_notices(notices(1), limit)
    assert encoder.calls == []


@pytest.mark.parametrize("text", [" ", "x" * 4001])
async def test_one_invalid_notice_rejects_entire_batch_before_embedding(text: str) -> None:
    encoder = RecordingEncoder()
    inputs = [*notices(16), Notice("invalid", text)]
    with pytest.raises(ServiceError):
        await SupplierSearch(RecordingIndex(), encoder).search_notices(inputs)
    assert encoder.calls == []


@pytest.mark.parametrize(
    "vectors",
    [[], [[1.0]], [[0.0, 0.0]], [[float("nan"), 1.0]], [[float("inf"), 1.0]]],
)
async def test_invalid_vectors_never_reach_index(vectors: list[list[float]]) -> None:
    encoder = RecordingEncoder()
    encoder.invalid = vectors
    index = RecordingIndex()
    with pytest.raises(ServiceError, match="вектор"):
        await SupplierSearch(index, encoder).search_notices(notices(1))
    assert index.calls == []
