import argparse
import asyncio
import json
from pathlib import Path

from src.adapter.repository.supplier_index.importer import import_index
from src.application.config import AppConfig
from src.application.container import Container


async def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    config = AppConfig.from_env()
    async with Container(config) as container:
        await (await container.migrator()).apply_pending()
        result = await import_index(
            await container.gateway(), config.clickhouse.database, args.directory
        )
        print(json.dumps(result))


if __name__ == "__main__":
    asyncio.run(run())
