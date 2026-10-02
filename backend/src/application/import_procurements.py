import argparse
import asyncio
import json
from pathlib import Path

from src.adapter.repository.procurement_import.importer import import_procurements
from src.application.config import AppConfig
from src.application.container import Container


async def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prepared", type=Path)
    parser.add_argument("index", type=Path)
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    config = AppConfig.from_env()
    async with Container(config) as container:
        await (await container.migrator()).apply_pending()
        report = await import_procurements(
            await container.gateway(),
            config.clickhouse.database,
            args.prepared,
            args.index,
            args.batch_size,
        )
        print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(run())
