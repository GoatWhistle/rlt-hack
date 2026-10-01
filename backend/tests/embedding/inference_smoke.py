import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.client.errors import EmbeddingClientError
from src.adapter.client.inference.client import InferenceEmbedder
from src.application.encoder import text_encoder


async def check():
    state = {"mode": "valid", "calls": 0}

    def respond(request):
        state["calls"] += 1
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": "qwen3-embedding:4b", "digest": "v1"}]}
            )
        assert request.url.path == "/v1/embeddings"
        body = json.loads(request.content)
        assert body["model"] == "Qwen/Qwen3-Embedding-4B"
        assert body["encoding_format"] == "float"
        if state["mode"] == "query":
            assert all(text.startswith("Instruct:") for text in body["input"])
        rows = [
            {"index": i, "embedding": [float(i + 1)] * 2560} for i in range(len(body["input"]))
        ][::-1]
        if state["mode"] == "duplicate":
            rows[0]["index"] = rows[-1]["index"]
        elif state["mode"] == "dimension":
            rows[0]["embedding"] = [1]
        elif state["mode"] == "empty":
            rows[0]["embedding"] = [0] * 2560
        elif state["mode"] == "nan":
            rows[0]["embedding"][0] = "NaN"
        elif state["mode"] == "missing":
            rows.pop()
        elif state["mode"] == "network":
            raise httpx.ConnectError("private detail", request=request)
        elif state["mode"] == "http":
            return httpx.Response(401, text="private detail")
        elif state["mode"] == "format":
            return httpx.Response(200, json={"wrong": True})
        return httpx.Response(200, json={"data": rows})

    async with httpx.AsyncClient(
        base_url="https://encoder.test/v1/", transport=httpx.MockTransport(respond)
    ) as http:
        encoder = InferenceEmbedder(http, "Qwen/Qwen3-Embedding-4B", "v1")
        assert (
            encoder.model_key != InferenceEmbedder(http, "Qwen/Qwen3-Embedding-4B", "v2").model_key
        )
        assert await encoder.encode([]) == [] and state["calls"] == 0
        vectors = await encoder.encode(["paper", "clothes"])
        assert vectors[0][0] == 1 and vectors[1][0] == 2
        state["mode"] = "query"
        await encoder.encode(["paper"], query=True)
        for mode in (
            "duplicate",
            "dimension",
            "empty",
            "nan",
            "missing",
            "network",
            "http",
            "format",
        ):
            state["mode"] = mode
            try:
                await encoder.encode(["paper", "clothes"])
            except EmbeddingClientError as error:
                assert "private detail" not in str(error)
            else:
                raise AssertionError(mode)
        for model, revision, dimensions in (
            ("Qwen/Qwen3-Embedding-0.6B", "v1", 2560),
            ("Qwen/Qwen3-Embedding-4B", "", 2560),
            ("Qwen/Qwen3-Embedding-4B", "v1", 1024),
        ):
            try:
                InferenceEmbedder(http, model, revision, dimensions)
            except EmbeddingClientError:
                pass
            else:
                raise AssertionError("Invalid model accepted")

    original = httpx.AsyncClient

    def client(**kwargs):
        assert kwargs["trust_env"] is False
        return original(**kwargs, transport=httpx.MockTransport(respond))

    environment = {
        "EMBEDDING_TRANSPORT": "inference",
        "EMBEDDING_INFERENCE_URL": "https://encoder.test/v1",
        "EMBEDDING_INFERENCE_REVISION": "v1",
        "EMBEDDING_INFERENCE_CACHE_KEY": "existing-vector-space",
    }
    state["mode"] = "valid"
    with (
        patch.dict(os.environ, environment, clear=True),
        patch("src.application.encoder.httpx.AsyncClient", side_effect=client),
    ):
        async with text_encoder() as encoder:
            assert encoder.model_key == "existing-vector-space"
            assert len((await encoder.encode(["paper"]))[0]) == 2560
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("src.application.encoder.httpx.AsyncClient", side_effect=client),
    ):
        async with text_encoder() as encoder:
            assert encoder.model_key.startswith("ollama/qwen3-embedding:4b@v1/")
    with patch.dict(os.environ, {"EMBEDDING_TRANSPORT": "unknown"}, clear=True):
        try:
            async with text_encoder():
                raise AssertionError("Invalid transport accepted")
        except EmbeddingClientError:
            pass
    print("Inference encoder checks passed")


if __name__ == "__main__":
    asyncio.run(check())
