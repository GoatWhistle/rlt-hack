import asyncio
import dataclasses
import json
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import httpx
from chdb.session import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.client.errors import EmbeddingClientError
from src.adapter.client.ollama.client import OllamaEmbedder
from src.adapter.repository.clickhouse.catalog.offer import ClickHouseOfferRepository
from src.adapter.repository.clickhouse.engine.migrator import Migrator
from src.adapter.repository.clickhouse.engine.versions import VersionSequencer
from src.adapter.repository.clickhouse.search.embedding import ClickHouseEmbeddingRepository
from src.models.catalog.offer import Offer
from src.models.enums import Availability
from src.service.embedding.worker import EmbeddingWorker
from src.service.errors import ServiceError
from tests.clickhouse.chdb_gateway import ChdbGateway


async def check() -> None:
    state = {"digest": "revision-one", "bad": False, "query": False}

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": "test:4b", "digest": state["digest"]}]}
            )
        body = json.loads(request.content)
        assert body["options"]["num_ctx"] == 512
        vectors = []
        for text in body["input"]:
            if text.startswith("Instruct:"):
                state["query"] = True
            vectors.append([0, 0] if state["bad"] else ([1, 0] if "бумага" in text else [0, 1]))
        return httpx.Response(200, json={"embeddings": vectors})

    with tempfile.TemporaryDirectory(prefix="rlt-embedding-") as directory:
        session = cast("Callable[[str], Any]", Session)(str(Path(directory) / "db"))
        try:
            gateway = ChdbGateway(session)
            await Migrator(gateway).apply_pending()
            versions = VersionSequencer()
            offers = ClickHouseOfferRepository(gateway, versions)
            now = datetime.now(UTC)
            first = Offer(
                uuid4(),
                uuid4(),
                "1",
                "https://example.test/1",
                "бумага",
                now,
                now,
                content_hash="paper-v1",
            )
            second = dataclasses.replace(
                first, offer_id=uuid4(), name="станок", content_hash="machine-v1"
            )
            await offers.save_many([first, second], now)
            repository = ClickHouseEmbeddingRepository(gateway, versions)
            async with httpx.AsyncClient(
                base_url="http://local.test", transport=httpx.MockTransport(respond)
            ) as http:
                encoder = OllamaEmbedder(http, "test:4b", dimensions=2)
                await encoder.initialize()
                worker = EmbeddingWorker(repository, encoder)
                assert await worker.run_once(2) == 2
                assert await worker.run_once(2) == 0
                hits = await worker.search("бумага")
                assert hits[0].offer_id == first.offer_id and state["query"]
                updated = dataclasses.replace(first, content_hash="paper-v2")
                await offers.save_many([updated], now)
                assert first.offer_id not in [hit.offer_id for hit in await worker.search("бумага")]
                state["bad"] = True
                try:
                    await worker.run_once()
                except ServiceError:
                    pass
                else:
                    raise AssertionError("нулевой вектор принят")
                assert len(await repository.pending(encoder.model_key, 2, 10)) == 1
                state["bad"] = False
                assert await worker.run_once() == 1
                await offers.save_many(
                    [dataclasses.replace(updated, availability=Availability.UNAVAILABLE)], now
                )
                assert first.offer_id not in [hit.offer_id for hit in await worker.search("бумага")]
                assert len(await repository.pending("other-model", 2, 10)) == 1
                assert len(await repository.pending(encoder.model_key, 3, 10)) == 1
                state["digest"] = "revision-two"
                try:
                    await encoder.encode(["test"])
                except EmbeddingClientError:
                    pass
                else:
                    raise AssertionError("подмена ревизии модели не обнаружена")
                missing = OllamaEmbedder(http, "missing:4b")
                try:
                    await missing.initialize()
                except EmbeddingClientError:
                    pass
                else:
                    raise AssertionError("отсутствующая модель принята")
        finally:
            session.close()
    print("Embedding: indexing, repeat, stale vectors, withdrawal, validation and revision passed")


if __name__ == "__main__":
    asyncio.run(check())
