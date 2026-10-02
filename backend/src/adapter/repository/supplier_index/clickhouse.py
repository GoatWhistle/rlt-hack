import asyncio
from dataclasses import replace
from pathlib import Path

import numpy as np

from src.adapter.repository.supplier_index.history import enrich_history
from src.adapter.repository.supplier_index.index import FileSupplierIndex
from src.adapter.repository.supplier_index.protocols import SqlGateway
from src.models.search_context import SearchContext
from src.models.supplier_search import SupplierCandidate, SupplierCatalogOffer


class ClickHouseSupplierIndex(FileSupplierIndex):
    def __init__(self, directory: Path, gateway: SqlGateway, index_id: str, database: str) -> None:
        super().__init__(directory)
        self._gateway = gateway
        self._index_id = index_id
        self._database = database

    async def initialize(self) -> None:
        await super().initialize()
        if self._index_id != self.manifest["files"]["card_vectors.npy"]:
            raise ValueError("ClickHouse index differs from card manifest")
        rows = await self._gateway.select(
            f"SELECT card_count, dimensions, cards_sha256 "
            f"FROM {self._database}.supplier_profile_indexes FINAL "
            "WHERE index_id = {index:String}",
            {"index": self._index_id},
        )
        if rows != [(len(self.cards), self.dimensions, self.manifest["files"]["cards.parquet"])]:
            raise ValueError("ClickHouse supplier index is not complete")
        self._positions = {card["card_id"]: i for i, card in enumerate(self.cards)}
        del self.vectors
        del self.norms

    async def search(self, text: str, vector: list[float], limit: int) -> list[SupplierCandidate]:
        return await self.search_context(text, vector, limit, SearchContext())

    async def search_context(
        self, text: str, vector: list[float], limit: int, context: SearchContext
    ) -> list[SupplierCandidate]:
        rows = await self._gateway.select(
            f"SELECT card_id, 1 - cosineDistance(embedding, {{vector:Array(Float32)}}) "
            f"FROM {self._database}.supplier_profile_embeddings FINAL "
            "WHERE index_id = {index:String}",
            {"index": self._index_id, "vector": vector},
        )
        if len(rows) != len(self.cards):
            raise ValueError("ClickHouse supplier index changed")
        candidates = await asyncio.to_thread(self._combine, text, rows, limit, context)
        return await self.enrich(candidates)

    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]:
        candidates = await super().enrich(candidates)
        if not candidates:
            return []
        parameters = {"inns": list({candidate.inn for candidate in candidates})}
        rows = await self._gateway.select(
            f"SELECT inn, name, website, contacts, identity_evidence_url "
            f"FROM {self._database}.suppliers_current WHERE inn IN {{inns:Array(String)}} "
            "ORDER BY updated_at DESC LIMIT 1 BY inn",
            parameters,
        )
        suppliers = {row[0]: row[1:] for row in rows}
        rows = await self._gateway.select(
            f"SELECT inn, name, region FROM {self._database}.msp_companies FINAL "
            "WHERE inn IN {inns:Array(String)}",
            parameters,
        )
        registry_names = {row[0]: row[1] for row in rows}
        registry_regions = {row[0]: row[2] for row in rows}
        rows = await self._gateway.select(
            "SELECT s.inn, o.name, o.url, toString(o.last_seen_at) "
            f"FROM {self._database}.offers_current o "
            f"INNER JOIN {self._database}.suppliers_current s ON o.supplier_id = s.supplier_id "
            "WHERE s.inn IN {inns:Array(String)} AND o.availability != 'unavailable' "
            "ORDER BY o.last_seen_at DESC, o.offer_id LIMIT 3 BY s.inn",
            parameters,
        )
        catalog: dict[str, list[SupplierCatalogOffer]] = {}
        for inn, name, url, date in rows:
            catalog.setdefault(inn, []).append(SupplierCatalogOffer(name, url, date[:10]))
        result = []
        for candidate in candidates:
            name, website, contacts, url = suppliers.get(candidate.inn, ("", "", {}, ""))
            result.append(
                replace(
                    candidate,
                    name=name or registry_names.get(candidate.inn, ""),
                    registered_region=registry_regions.get(candidate.inn, ""),
                    website=website,
                    email=contacts.get("email", ""),
                    phone=contacts.get("phone", ""),
                    identity_url=url,
                    catalog=catalog.get(candidate.inn, []),
                )
            )
        return await enrich_history(self._gateway, self._database, self._index_id, result)

    def _combine(
        self, text: str, rows: list[tuple], limit: int, context: SearchContext | None = None
    ) -> list[SupplierCandidate]:
        dense = np.zeros(len(self.cards), dtype=np.float32)
        for card_id, score in rows:
            dense[self._positions[card_id]] = score
        if not np.isfinite(dense).all():
            raise ValueError("Invalid ClickHouse distances")
        return self._fuse(text, dense, limit, context)
