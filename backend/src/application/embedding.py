import os
from contextlib import asynccontextmanager

import httpx

from src.adapter.client.ollama.client import OllamaEmbedder
from src.adapter.repository.clickhouse.embedding import ClickHouseEmbeddingRepository
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.application.config import AppConfig
from src.application.container import Container
from src.service.embedding.worker import EmbeddingWorker


@asynccontextmanager
async def embedding_worker():
    config = AppConfig.from_env()
    async with (
        Container(config) as container,
        httpx.AsyncClient(
            base_url=os.getenv("EMBEDDING_URL", "http://127.0.0.1:11435"),
            timeout=httpx.Timeout(180, connect=10),
            trust_env=False,
        ) as http,
    ):
        encoder = OllamaEmbedder(
            http,
            model=os.getenv("EMBEDDING_MODEL", "qwen3-embedding:4b"),
            dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "2560")),
            context_length=int(os.getenv("EMBEDDING_CONTEXT_LENGTH", "512")),
            expected_digest=os.getenv("EMBEDDING_MODEL_DIGEST", ""),
        )
        await encoder.initialize()
        repository = ClickHouseEmbeddingRepository(
            await container.gateway(), VersionSequencer(), config.clickhouse.database
        )
        yield EmbeddingWorker(repository, encoder)
