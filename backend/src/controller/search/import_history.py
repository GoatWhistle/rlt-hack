import argparse
import asyncio
import json
from pathlib import Path

from src.adapter.repository.supplier_index.history_import import import_history
from src.application.config import AppConfig
from src.application.container import Container


async def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("prepared", type=Path)
    parser.add_argument("index", type=Path)
    args = parser.parse_args()
    config = AppConfig.from_env()
    async with Container(config) as container:
        await (await container.migrator()).apply_pending()
        report = await import_history(
            await container.gateway(), config.clickhouse.database, args.prepared, args.index
        )
        print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(run())
