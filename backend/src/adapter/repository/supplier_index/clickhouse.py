import asyncio
from pathlib import Path

import numpy as np

from src.adapter.repository.supplier_index.index import FileSupplierIndex
from src.adapter.repository.supplier_index.protocols import SqlGateway
from src.models.supplier_search import SupplierCandidate


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
        rows = await self._gateway.select(
            f"SELECT card_id, 1 - cosineDistance(embedding, {{vector:Array(Float32)}}) "
            f"FROM {self._database}.supplier_profile_embeddings FINAL "
            "WHERE index_id = {index:String}",
            {"index": self._index_id, "vector": vector},
        )
        if len(rows) != len(self.cards):
            raise ValueError("ClickHouse supplier index changed")
        return await asyncio.to_thread(self._combine, text, rows, limit)

    def _combine(self, text: str, rows: list[tuple], limit: int) -> list[SupplierCandidate]:
        dense = np.zeros(len(self.cards), dtype=np.float32)
        for card_id, score in rows:
            dense[self._positions[card_id]] = score
        if not np.isfinite(dense).all():
            raise ValueError("Invalid ClickHouse distances")
        return self._fuse(text, dense, limit)
