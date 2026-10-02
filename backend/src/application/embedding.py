import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from src.adapter.repository.clickhouse.engine.versions import VersionSequencer
from src.adapter.repository.clickhouse.search.embedding import ClickHouseEmbeddingRepository
from src.application.config import AppConfig
from src.application.container import Container
from src.application.encoder import text_encoder
from src.service.embedding.worker import EmbeddingWorker


@asynccontextmanager
async def embedding_worker() -> AsyncIterator[EmbeddingWorker]:
    config = AppConfig.from_env()
    async with (
        Container(config) as container,
        text_encoder(
            dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "2560")),
            context_length=int(os.getenv("EMBEDDING_CONTEXT_LENGTH", "512")),
        ) as encoder,
    ):
        repository = ClickHouseEmbeddingRepository(
            await container.gateway(), VersionSequencer(), config.clickhouse.database
        )
        yield EmbeddingWorker(repository, encoder)
