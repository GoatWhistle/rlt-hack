"""Ожидание полного батча, сброс хвоста и сохранение одной операцией."""

import asyncio
import sys
from contextlib import suppress
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.models.embedding import EmbeddingDocument
from src.service.embedding.worker import EmbeddingWorker


class Repository:
    def __init__(self):
        self.documents = []
        self.saved = []
        self.polled = asyncio.Event()
        self.written = asyncio.Event()

    async def pending(self, model, dimensions, limit):
        self.polled.set()
        return self.documents[:limit]

    async def save(self, documents, vectors, model):
        self.saved.append((documents, vectors))
        del self.documents[: len(documents)]
        self.written.set()


class Encoder:
    model_key = "synthetic"
    dimensions = 2

    async def encode(self, texts, query=False):
        return [[1.0, 0.0] for _ in texts]


def document():
    return EmbeddingDocument(uuid4(), "hash", "synthetic")


async def check():
    repository = Repository()
    repository.documents = [document()]
    worker = EmbeddingWorker(repository, Encoder())
    task = asyncio.create_task(worker.run_forever(2, 0.1))
    try:
        await asyncio.wait_for(repository.polled.wait(), 1)
        assert not repository.saved
        repository.documents.append(document())
        await asyncio.wait_for(repository.written.wait(), 1)
        assert len(repository.saved) == 1 and len(repository.saved[0][0]) == 2
        repository.written.clear()
        repository.documents.append(document())
        await asyncio.wait_for(repository.written.wait(), 1)
        assert len(repository.saved) == 2 and len(repository.saved[1][0]) == 1
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    print("Embedding batch accumulation and timeout flush OK")


if __name__ == "__main__":
    asyncio.run(check())
