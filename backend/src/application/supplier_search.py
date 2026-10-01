import os
from contextlib import asynccontextmanager

import httpx

from src.adapter.client.ollama.client import OllamaEmbedder
from src.application.supplier_index import supplier_index
from src.service.search.supplier import SupplierSearch


@asynccontextmanager
async def supplier_search():
    async with (
        supplier_index() as index,
        httpx.AsyncClient(
            base_url=os.getenv("EMBEDDING_URL", "http://127.0.0.1:11435"),
            timeout=httpx.Timeout(180, connect=10),
            trust_env=False,
        ) as http,
    ):
        encoder = OllamaEmbedder(
            http,
            model=os.getenv("EMBEDDING_MODEL", "qwen3-embedding:4b"),
            dimensions=index.dimensions,
            context_length=256,
            expected_digest=os.getenv("EMBEDDING_MODEL_DIGEST", ""),
        )
        await encoder.initialize()
        yield SupplierSearch(index, encoder)
