import json
from typing import Any

import httpx
import pytest

from src.adapter.client.errors import MlProtocolError, MlServiceError, MlServiceUnavailableError
from src.adapter.client.profile_similarity.client import ProfileSimilarityClient

INDEX = "a" * 64
VECTOR = [1.0] + [0.0] * 2559


async def test_profile_scores_validate_artifact_order_and_send_only_vector() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/profile-scores"
        assert json.loads(request.content) == {"index_id": INDEX, "vector": VECTOR}
        return httpx.Response(200, json={"index_id": INDEX, "scores": [0.5, 0.1]})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="http://gpu/"
    ) as http:
        assert await ProfileSimilarityClient(http).score(INDEX, VECTOR, 2) == [0.5, 0.1]


@pytest.mark.parametrize(
    "payload",
    [
        {"index_id": "foreign", "scores": [0.5, 0.1]},
        {"index_id": INDEX, "scores": [0.5]},
        {"index_id": INDEX, "scores": [True, 0.1]},
        {"index_id": INDEX, "scores": ["0.5", 0.1]},
        {"index_id": INDEX, "scores": [float("nan"), 0.1]},
        {"index_id": INDEX, "scores": [float("inf"), 0.1]},
    ],
)
async def test_mismatched_or_nonfinite_profile_scores_fail(payload: dict[str, Any]) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps(payload).encode())

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="http://gpu/"
    ) as http:
        with pytest.raises(MlProtocolError):
            await ProfileSimilarityClient(http).score(INDEX, VECTOR, 2)


async def test_profile_channel_failure_is_explicit() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="http://gpu/"
    ) as http:
        with pytest.raises(MlServiceError) as failure:
            await ProfileSimilarityClient(http).score(INDEX, VECTOR, 2)
        assert failure.value.status == 503

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(timeout), base_url="http://gpu/"
    ) as http:
        with pytest.raises(MlServiceUnavailableError):
            await ProfileSimilarityClient(http).score(INDEX, VECTOR, 2)
        with pytest.raises(MlProtocolError):
            await ProfileSimilarityClient(http).score(INDEX, [0.0] * 2560, 2)
