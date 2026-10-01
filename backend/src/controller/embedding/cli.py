import argparse
import asyncio
import dataclasses
import json
import logging
import time

from src.application.embedding import embedding_worker
from src.controller.embedding.protocols import OfferEmbedding


async def dispatch(worker: OfferEmbedding, args: argparse.Namespace) -> None:
    started = time.monotonic()
    if args.command == "index":
        if args.forever:
            await worker.run_forever(args.batch_size, args.interval)
        else:
            count = await worker.run_once(args.batch_size, args.max_batches)
            print(json.dumps({"indexed": count, "seconds": time.monotonic() - started}))
    else:
        hits = await worker.search(args.text, args.limit)
        print(
            json.dumps(
                {
                    "hits": [dataclasses.asdict(hit) for hit in hits],
                    "seconds": time.monotonic() - started,
                },
                ensure_ascii=False,
                default=str,
            )
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Локальная векторизация и поиск предложений")
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index")
    index.add_argument("--batch-size", type=int, default=1)
    index.add_argument("--max-batches", type=int, default=1)
    index.add_argument("--forever", action="store_true")
    index.add_argument("--interval", type=float, default=30)
    search = commands.add_parser("search")
    search.add_argument("text")
    search.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    async with embedding_worker() as worker:
        await dispatch(worker, args)


if __name__ == "__main__":
    asyncio.run(main())
