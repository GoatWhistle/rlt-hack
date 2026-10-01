import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx

from bench import load, seed, stages
from bench.clickhouse import ClickHouseAddress, ClickHouseHttp
from bench.queries import QUERIES
from bench.sql import Volume

REPOSITORY = Path(__file__).resolve().parents[2]
SERVICES = ("clickhouse", "migrate", "api")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m bench.run")
    parser.add_argument("--up", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--project", default="rlt-bench")
    parser.add_argument("--pool-size", type=int)
    parser.add_argument("--max-threads", type=int)
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--sequential", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--clickhouse-url", default="http://localhost:8123")
    parser.add_argument("--label", default="")
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


async def _compose(arguments: argparse.Namespace) -> None:
    environment = dict(os.environ)
    if arguments.pool_size is not None:
        environment["CLICKHOUSE_POOL_SIZE"] = str(arguments.pool_size)
    if arguments.max_threads is not None:
        environment["CLICKHOUSE_MAX_THREADS"] = str(arguments.max_threads)
    command = ["docker", "compose", "-p", arguments.project, "up", "-d", "--wait"]
    if arguments.build:
        command.append("--build")
    process = await asyncio.create_subprocess_exec(
        *command, *SERVICES, cwd=REPOSITORY, env=environment
    )
    if await process.wait() != 0:
        raise RuntimeError("docker compose up failed")


async def _measure(arguments: argparse.Namespace, clickhouse: ClickHouseHttp) -> list[object]:
    modes: list[object] = []
    plan = [
        ("sequential", 1, arguments.sequential),
        ("concurrent", arguments.concurrency, arguments.requests),
    ]
    timeout = httpx.Timeout(60.0)
    async with httpx.AsyncClient(base_url=arguments.api_url, timeout=timeout) as client:
        await load.wait_ready(client, 180)
        await load.run(client, QUERIES[: arguments.warmup], "warmup", 1, arguments.warmup)
        for name, concurrency, total in plan:
            started = int(time.time())
            mode = await load.run(client, QUERIES, name, concurrency, total)
            finished = int(time.time()) + 1
            report = load.summary(mode)
            report["stages"] = await stages.breakdown(clickhouse, started, finished)
            modes.append(report)
    return modes


async def main() -> None:
    arguments = _arguments()
    if arguments.up:
        await _compose(arguments)
    address = ClickHouseAddress(url=arguments.clickhouse_url)
    async with ClickHouseHttp(address) as clickhouse:
        seeding = await seed.seed(clickhouse, Volume(), arguments.reset) if arguments.seed else {}
        report = {
            "label": arguments.label,
            "pool_size": arguments.pool_size,
            "max_threads": arguments.max_threads,
            "seed_seconds": seeding,
            "rows": await seed.counts(clickhouse),
            "modes": await _measure(arguments, clickhouse),
        }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if arguments.out is not None:
        arguments.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text + "\n")


if __name__ == "__main__":
    asyncio.run(main())
