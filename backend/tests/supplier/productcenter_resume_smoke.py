"""Возобновление подтверждённых порций без повторного чтения карточек."""

import asyncio
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.supplier.productcenter_smoke import G1, pages, provider


async def check():
    with tempfile.TemporaryDirectory() as directory:
        cache = Path(directory)
        data = pages()
        adapter = provider(data, cache_dir=cache)
        started = await adapter.resume(datetime.now(UTC))
        stream = adapter.batches(1)
        first = await anext(stream)
        assert first.offers[0].external_id == "21"
        assert adapter.saved_offer_count == 0
        await anext(stream)
        assert adapter.saved_offer_count == 1
        await stream.aclose()
        assert (cache / "crawl-progress.json").exists()
        await adapter._cache.invalidate(G1)
        del data[G1]
        resumed = provider(data, cache_dir=cache)
        assert await resumed.resume(datetime.now(UTC)) == started
        remaining = [package async for package in resumed.batches(1)]
        assert [offer.external_id for package in remaining for offer in package.offers] == ["22"]
        assert resumed.saved_offer_count == 2
        await resumed.complete()
        assert not (cache / "crawl-progress.json").exists()
    print("ProductCenter: checkpoint acknowledgement and resume OK")


if __name__ == "__main__":
    asyncio.run(check())
