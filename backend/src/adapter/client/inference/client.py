import hashlib
import math

import httpx

from src.adapter.client.errors import EmbeddingClientError
from src.adapter.client.ollama.client import QUERY_INSTRUCTION


class InferenceEmbedder:
    def __init__(
        self,
        http: httpx.AsyncClient,
        model: str,
        revision: str,
        dimensions: int = 2560,
        cache_key: str = "",
    ) -> None:
        if model.casefold() != "qwen/qwen3-embedding-4b" or dimensions != 2560 or not revision:
            raise EmbeddingClientError("ожидается фиксированная ревизия Qwen 4B, размерность 2560")
        self._http = http
        self._model = model
        self.dimensions = dimensions
        signature = hashlib.sha256((str(http.base_url).rstrip("/") + model).encode()).hexdigest()
        self.model_key = cache_key or (
            f"inference/{revision}/{signature}/offer-v1-query-v1/dim{dimensions}"
        )

    async def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        if not texts:
            return []
        inputs = (
            [f"Instruct: {QUERY_INSTRUCTION}\nQuery: {text}" for text in texts] if query else texts
        )
        try:
            response = await self._http.post(
                "embeddings",
                json={"model": self._model, "input": inputs, "encoding_format": "float"},
            )
            response.raise_for_status()
            data = sorted(response.json()["data"], key=lambda item: item["index"])
            if [item["index"] for item in data] != list(range(len(texts))):
                raise ValueError("invalid response order")
            vectors = [[float(value) for value in item["embedding"]] for item in data]
            if any(
                len(vector) != self.dimensions
                or not all(math.isfinite(value) for value in vector)
                or not any(vector)
                for vector in vectors
            ):
                raise ValueError("invalid vector")
            return vectors
        except (httpx.HTTPError, KeyError, TypeError, ValueError, OverflowError):
            raise EmbeddingClientError("не удалось получить корректные векторы 4B") from None
