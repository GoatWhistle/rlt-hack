import asyncio
import dataclasses
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.client.ollama.client import OllamaEmbedder
from src.adapter.repository.clickhouse.embedding import ClickHouseEmbeddingRepository
from src.adapter.repository.clickhouse.migrator import MIGRATION_DIR, split_statements
from src.adapter.repository.clickhouse.offer import ClickHouseOfferRepository
from src.adapter.repository.clickhouse.source import ClickHouseSourceRepository
from src.adapter.repository.clickhouse.supplier import ClickHouseSupplierRepository
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.adapter.supplier import identity, page
from src.adapter.supplier.productcenter_web.discovery import listing_links
from src.adapter.supplier.productcenter_web.parse import product_card, supplier_card
from src.application.config import AppConfig
from src.application.container import Container
from src.models.enums import SourceType
from src.models.source import Source
from src.service.embedding.worker import EmbeddingWorker


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    started = time.monotonic()
    database = "embedding_diagnostic_" + datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    base = "https://productcenter.ru"
    source = Source(
        identity.source_id(base, "productcenter_diagnostic"),
        "ProductCenter: диагностическая выборка, не полный каталог",
        base,
        SourceType.DIRECTORY,
        "productcenter_diagnostic",
    )
    offers = []
    suppliers = {}
    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as http:
        response = await http.get(f"{base}/products")
        response.raise_for_status()
        tree = await asyncio.to_thread(page.parse, response.text, str(response.url))
        urls, _, _ = listing_links(tree, "products")
        for url in list(urls.values())[:6]:
            response = await http.get(url)
            response.raise_for_status()
            offer = await asyncio.to_thread(
                product_card, response.text, url, source.source_id, datetime.now(UTC)
            )
            owner_url = urljoin(base, offer.evidence_url)
            if owner_url not in suppliers:
                response = await http.get(owner_url)
                response.raise_for_status()
                suppliers[owner_url] = await asyncio.to_thread(
                    supplier_card, response.text, owner_url, source.source_id
                )
            offers.append(dataclasses.replace(offer, supplier_id=suppliers[owner_url].supplier_id))
    if not offers:
        raise RuntimeError("диагностическая выборка пуста")
    config = AppConfig.from_env()
    async with (
        Container(config) as container,
        httpx.AsyncClient(
            base_url=os.getenv("EMBEDDING_URL", "http://embedder:11434"),
            timeout=180,
            trust_env=False,
        ) as http,
    ):
        gateway = await container.gateway()
        await gateway.command(f"CREATE DATABASE {database}")
        paths = await asyncio.to_thread(lambda: sorted(MIGRATION_DIR.glob("*.sql")))
        for path in paths:
            sql = await asyncio.to_thread(path.read_text)
            for statement in split_statements(sql.replace("supplier_search", database)):
                await gateway.command(statement)
        versions = VersionSequencer()
        await ClickHouseSourceRepository(gateway, versions, database).save_many([source])
        await ClickHouseSupplierRepository(gateway, versions, database).save_many(
            list(suppliers.values())
        )
        await ClickHouseOfferRepository(gateway, versions, database).save_many(
            offers, datetime.now(UTC)
        )
        encoder = OllamaEmbedder(http, os.getenv("EMBEDDING_MODEL", "qwen3-embedding:4b"))
        await encoder.initialize()
        worker = EmbeddingWorker(
            ClickHouseEmbeddingRepository(gateway, versions, database), encoder
        )
        indexing_start = time.monotonic()
        indexed = await worker.run_once(1, len(offers))
        indexing_seconds = time.monotonic() - indexing_start
        repeat = await worker.run_once(1, len(offers))
        if indexed != len(offers) or repeat:
            raise RuntimeError("индексация или повторная обработка не прошла")
        query_results = []
        for offer in offers[:3]:
            query_start = time.monotonic()
            hits = await worker.search(offer.name, 3)
            if not hits:
                raise RuntimeError("поиск не вернул результатов")
            query_results.append(
                {
                    "query": offer.name,
                    "seconds": time.monotonic() - query_start,
                    "self_in_top3": any(hit.offer_id == offer.offer_id for hit in hits),
                    "hits": [dataclasses.asdict(hit) for hit in hits],
                }
            )
        report = {
            "database": database,
            "status": "success",
            "model_key": encoder.model_key,
            "source_revision": os.getenv("SOURCE_REVISION", ""),
            "sample_kind": "six live cards; not full crawl or relevance benchmark",
            "offers": len(offers),
            "suppliers": len(suppliers),
            "indexed": indexed,
            "repeat_indexed": repeat,
            "indexing_seconds": indexing_seconds,
            "total_seconds": time.monotonic() - started,
            "queries": query_results,
        }
        output = Path("/reports/embedding-live.json")
        await asyncio.to_thread(output.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(
            output.write_text, json.dumps(report, ensure_ascii=False, indent=2, default=str)
        )
        print(json.dumps({key: value for key, value in report.items() if key != "queries"}))
        print(
            json.dumps(
                {
                    "query_seconds": [item["seconds"] for item in query_results],
                    "self_in_top3": [item["self_in_top3"] for item in query_results],
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
