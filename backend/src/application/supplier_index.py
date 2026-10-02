import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from src.adapter.repository.ranker.model import CandidateRanker
from src.adapter.repository.supplier_index.clickhouse import ClickHouseSupplierIndex
from src.adapter.repository.supplier_index.index import FileSupplierIndex
from src.application.config import AppConfig
from src.application.container import Container
from src.application.deferred_gateway import DeferredGateway


@asynccontextmanager
async def supplier_index():
    directory = Path(os.environ["SUPPLIER_INDEX_DIR"])
    index_id = os.getenv("SUPPLIER_INDEX_ID", "")
    if index_id:
        config = AppConfig.from_env()
        async with Container(config) as container:
            index = ClickHouseSupplierIndex(
                directory, DeferredGateway(container.gateway), index_id, config.clickhouse.database
            )
            await index.initialize()
            await initialize_ranker(index)
            yield index
    else:
        index = FileSupplierIndex(directory)
        await index.initialize()
        await initialize_ranker(index)
        yield index


async def initialize_ranker(index: FileSupplierIndex) -> None:
    configured = os.getenv("SUPPLIER_RANKER_DIR", "")
    directory = Path(configured) if configured else index.directory / "ranker"
    if configured or await asyncio.to_thread((directory / "runtime.json").is_file):
        ranker = CandidateRanker(directory)
        await ranker.initialize(index.cards, index.manifest["files"]["cards.parquet"])
        index.ranker = ranker
