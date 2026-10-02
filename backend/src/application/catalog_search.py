from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from src.adapter.repository.clickhouse.embedding import ClickHouseEmbeddingRepository
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.application.config import AppConfig
from src.application.container import Container
from src.application.encoder import text_encoder
from src.service.catalog_search.service import CatalogSearch


@asynccontextmanager
async def catalog_search() -> AsyncIterator[CatalogSearch]:
    config = AppConfig.from_env()
    async with Container(config) as container, text_encoder() as encoder:
        repository = ClickHouseEmbeddingRepository(
            await container.gateway(), VersionSequencer(), config.clickhouse.database
        )
        yield CatalogSearch(repository, encoder)
