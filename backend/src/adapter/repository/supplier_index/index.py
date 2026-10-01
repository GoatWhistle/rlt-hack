import asyncio
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as parquet
from sklearn.feature_extraction.text import CountVectorizer

from src.models.supplier_search import SupplierCandidate


class FileSupplierIndex:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.dimensions = 0
        self.instruction = ""

    async def initialize(self) -> None:
        await asyncio.to_thread(self._load)

    def _load(self) -> None:
        manifest = json.loads((self.directory / "manifest.json").read_text())
        self.manifest = manifest
        for name in ("card_vectors.npy", "cards.parquet", "report.json"):
            with (self.directory / name).open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != manifest["files"][name]:
                    raise ValueError("supplier index checksum mismatch")
        self.cards = parquet.read_table(self.directory / "cards.parquet").to_pylist()
        self.vectors = np.load(
            self.directory / "card_vectors.npy", mmap_mode="r", allow_pickle=False
        )
        if list(self.vectors.shape) != manifest["shape"] or len(self.cards) != len(self.vectors):
            raise ValueError("supplier index shape mismatch")
        self.dimensions = self.vectors.shape[1]
        self.instruction = manifest["query_instruction"]
        self.norms = np.empty(len(self.vectors), dtype=np.float32)
        for start in range(0, len(self.vectors), 1024):
            batch = self.vectors[start : start + 1024]
            if not np.isfinite(batch).all():
                raise ValueError("invalid supplier vectors")
            self.norms[start : start + len(batch)] = np.linalg.norm(batch, axis=1)
        if (self.norms <= 0).any():
            raise ValueError("empty supplier vectors")
        self.vectorizer = CountVectorizer(max_features=120000, dtype=np.float32)
        self.lexical = self.vectorizer.fit_transform(
            [card["profile_text"] for card in self.cards]
        ).tocsr()
        lengths = np.asarray(self.lexical.sum(axis=1)).ravel()
        frequency = np.asarray((self.lexical > 0).sum(axis=0)).ravel()
        idf = np.log1p((len(self.cards) - frequency + 0.5) / (frequency + 0.5))
        normalization = 1.2 * (0.25 + 0.75 * lengths / max(float(lengths.mean()), 1))
        rows = np.repeat(np.arange(len(self.cards)), np.diff(self.lexical.indptr))
        self.lexical.data = (
            self.lexical.data
            * 2.2
            / (self.lexical.data + normalization[rows])
            * idf[self.lexical.indices]
        ).astype(np.float32)

    async def search(self, text: str, vector: list[float], limit: int) -> list[SupplierCandidate]:
        return await asyncio.to_thread(self._search, text, vector, limit)

    def _ranking(self, scores: np.ndarray, *, positive: bool = False) -> dict[str, int]:
        result = {}
        for position in np.argsort(-scores, kind="stable"):
            if positive and scores[position] <= 0:
                break
            inn = self.cards[position]["supplier_inn"]
            if inn not in result:
                result[inn] = int(position)
            if len(result) == 300:
                break
        return result

    def _search(self, text: str, vector: list[float], limit: int) -> list[SupplierCandidate]:
        query = np.asarray(vector, dtype=np.float32)
        query /= np.linalg.norm(query)
        dense = (self.vectors @ query) / self.norms
        return self._fuse(text, dense, limit)

    def _fuse(self, text: str, dense: np.ndarray, limit: int) -> list[SupplierCandidate]:
        lexical = (self.lexical @ self.vectorizer.transform([text]).sign().T).toarray().ravel()
        scores: dict[str, float] = {}
        positions: dict[str, int] = {}
        for ranking in (self._ranking(dense), self._ranking(lexical, positive=True)):
            for rank, (inn, position) in enumerate(ranking.items(), 1):
                scores[inn] = scores.get(inn, 0) + 1 / (60 + rank)
                positions.setdefault(inn, position)
        selected = sorted(scores, key=lambda inn: (-scores[inn], inn))[:limit]
        return [
            SupplierCandidate(
                inn=inn,
                category=self.cards[positions[inn]]["category"],
                profile=self.cards[positions[inn]]["profile_text"],
                score=scores[inn],
                similarity=float(dense[positions[inn]]),
            )
            for inn in selected
        ]
