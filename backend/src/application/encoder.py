import os
from contextlib import asynccontextmanager

import httpx

from src.adapter.client.errors import EmbeddingClientError
from src.adapter.client.inference.client import InferenceEmbedder
from src.adapter.client.ollama.client import OllamaEmbedder


@asynccontextmanager
async def text_encoder(*, dimensions: int = 2560, context_length: int = 512):
    transport = os.getenv("EMBEDDING_TRANSPORT", "ollama")
    if transport not in {"ollama", "inference"}:
        raise EmbeddingClientError("неизвестный транспорт энкодера")
    remote = transport == "inference"
    endpoint = (
        os.environ["EMBEDDING_INFERENCE_URL"]
        if remote
        else os.getenv("EMBEDDING_URL", "http://127.0.0.1:11435")
    )
    token = os.getenv("EMBEDDING_INFERENCE_TOKEN", "") if remote else ""
    async with httpx.AsyncClient(
        base_url=endpoint.rstrip("/") + "/",
        headers={"Authorization": "Bearer " + token} if token else {},
        timeout=httpx.Timeout(180, connect=10),
        trust_env=False,
    ) as http:
        if remote:
            encoder = InferenceEmbedder(
                http,
                model=os.getenv("EMBEDDING_INFERENCE_MODEL", "Qwen/Qwen3-Embedding-4B"),
                revision=os.environ["EMBEDDING_INFERENCE_REVISION"],
                dimensions=dimensions,
                cache_key=os.getenv("EMBEDDING_INFERENCE_CACHE_KEY", ""),
            )
        else:
            encoder = OllamaEmbedder(
                http,
                model=os.getenv("EMBEDDING_MODEL", "qwen3-embedding:4b"),
                dimensions=dimensions,
                context_length=context_length,
                expected_digest=os.getenv("EMBEDDING_MODEL_DIGEST", ""),
            )
            await encoder.initialize()
        yield encoder
