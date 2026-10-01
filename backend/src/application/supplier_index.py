import os
from contextlib import asynccontextmanager
from pathlib import Path

from src.adapter.repository.supplier_index.clickhouse import ClickHouseSupplierIndex
from src.adapter.repository.supplier_index.index import FileSupplierIndex
from src.application.config import AppConfig
from src.application.container import Container


@asynccontextmanager
async def supplier_index():
    directory = Path(os.environ["SUPPLIER_INDEX_DIR"])
    index_id = os.getenv("SUPPLIER_INDEX_ID", "")
    if index_id:
        config = AppConfig.from_env()
        async with Container(config) as container:
            index = ClickHouseSupplierIndex(
                directory, await container.gateway(), index_id, config.clickhouse.database
            )
            await index.initialize()
            yield index
    else:
        index = FileSupplierIndex(directory)
        await index.initialize()
        yield index
