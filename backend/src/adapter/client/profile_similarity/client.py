import asyncio
import json
import math

import httpx

from src.adapter.client.errors import MlProtocolError, MlServiceError, MlServiceUnavailableError


class ProfileSimilarityClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def score(self, index_id: str, vector: list[float], card_count: int) -> list[float]:
        if (
            len(vector) != 2560
            or not all(math.isfinite(value) for value in vector)
            or not any(vector)
        ):
            raise MlProtocolError("Profile similarity requires a nonempty finite Qwen 4B vector")
        try:
            response = await self._http.post(
                "profile-scores",
                json={"index_id": index_id, "vector": vector},
            )
        except httpx.HTTPError as error:
            raise MlServiceUnavailableError(type(error).__name__) from error
        if response.is_error:
            raise MlServiceError(response.status_code)
        return await asyncio.to_thread(_scores, response.content, index_id, card_count)


def _scores(content: bytes, index_id: str, card_count: int) -> list[float]:
    try:
        if len(content) > card_count * 40 + 1024:
            raise ValueError("oversized similarity response")
        payload: object = json.loads(content)
        if not isinstance(payload, dict):
            raise ValueError("similarity response is not an object")
        if payload["index_id"] != index_id:
            raise ValueError("similarity index identity differs")
        values = payload["scores"]
        if not isinstance(values, list) or len(values) != card_count:
            raise ValueError("similarity card count differs")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
            raise ValueError("non-numeric similarity scores")
        scores = [float(value) for value in values]
        if not all(math.isfinite(value) for value in scores):
            raise ValueError("non-finite similarity scores")
        return scores
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise MlProtocolError("Invalid profile similarity response") from error
