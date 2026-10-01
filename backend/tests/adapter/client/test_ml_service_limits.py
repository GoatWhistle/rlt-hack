import httpx
import pytest

from src.adapter.client.errors import MlProtocolError
from src.adapter.client.ml_service.retriever import CANDIDATE_OVERSAMPLING, MAX_RESPONSE_BYTES
from tests.adapter.client.test_ml_service import FakeIdentity, answer, regional_request, retriever


async def test_oversized_response_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b" " * (MAX_RESPONSE_BYTES + 1))

    with pytest.raises(MlProtocolError, match="too large"):
        await retriever(handler).retrieve(regional_request(), 10)


async def test_candidates_are_capped_before_identity_lookup() -> None:
    limit = 2
    many = [{"supplierInn": f"{index:010d}", "rank": index} for index in range(1, 200)]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=answer(many))

    identity = FakeIdentity()
    await retriever(handler, identity).retrieve(regional_request(), limit)
    assert len(identity.asked[0]) == limit * CANDIDATE_OVERSAMPLING
    assert identity.asked[0][0] == "0000000001"
