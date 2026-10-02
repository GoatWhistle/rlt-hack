import asyncio
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from pyarrow import parquet
from sklearn.feature_extraction.text import CountVectorizer

from src.adapter.repository.reference.loader import read_json
from src.adapter.repository.reference.okpd2 import FileOkpd2Reference
from src.adapter.repository.supplier_index.category_priority import (
    requested_categories,
    supplier_category_coverage,
)
from src.adapter.repository.supplier_index.protocols import CandidateRanking
from src.models.search.search_context import SearchContext
from src.models.search.supplier_search import SupplierCandidate


class FileSupplierIndex:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.dimensions = 0
        self.instruction = ""
        self.ranker: CandidateRanking | None = None

    @property
    def version(self) -> str:
        model = self.ranker.version if self.ranker is not None else "rrf"
        return self.manifest["files"]["card_vectors.npy"] + "/" + model

    async def initialize(self) -> None:
        document = await read_json(Path(__file__).resolve().parents[4] / "reference" / "okpd2.json")
        self.categories = FileOkpd2Reference.of(document, str.casefold)
        await asyncio.to_thread(self._load)

    def _load(self) -> None:
        manifest = json.loads((self.directory / "manifest.json").read_text())
        self.manifest = manifest
        for name in ("card_vectors.npy", "cards.parquet", "report.json"):
            with (self.directory / name).open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != manifest["files"][name]:
                    raise ValueError("supplier index checksum mismatch")
        self.cards = parquet.read_table(self.directory / "cards.parquet").to_pylist()
        self._cards_by_key = {(card["supplier_inn"], card["category"]): card for card in self.cards}
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

    async def search_context(
        self, text: str, vector: list[float], limit: int, context: SearchContext
    ) -> list[SupplierCandidate]:
        return await asyncio.to_thread(self._search, text, vector, limit, context)

    async def enrich(self, candidates: list[SupplierCandidate]) -> list[SupplierCandidate]:
        return [self._metadata(candidate) for candidate in candidates]

    def _metadata(self, candidate: SupplierCandidate) -> SupplierCandidate:
        card = self._cards_by_key.get((candidate.inn, candidate.category))
        if card is None:
            return candidate
        date = card.get("profile_last_date")
        return replace(
            candidate,
            category_name=self.categories.name_of(candidate.category),
            history_examples=[
                line.strip() for line in card["profile_text"].splitlines() if line.strip()
            ],
            history_last_date=str(date)[:10] if date else "",
        )

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

    def _search(
        self, text: str, vector: list[float], limit: int, context: SearchContext | None = None
    ) -> list[SupplierCandidate]:
        query = np.asarray(vector, dtype=np.float32)
        query /= np.linalg.norm(query)
        dense = (self.vectors @ query) / self.norms
        return self._fuse(text, dense, limit, context)

    def _fuse(
        self, text: str, dense: np.ndarray, limit: int, context: SearchContext | None = None
    ) -> list[SupplierCandidate]:
        lexical = (self.lexical @ self.vectorizer.transform([text]).sign().T).toarray().ravel()
        scores: dict[str, float] = {}
        positions: dict[str, int] = {}
        dense_order = self._ranking(dense)
        lexical_order = self._ranking(lexical, positive=True)
        for ranking in (dense_order, lexical_order):
            for rank, (inn, position) in enumerate(ranking.items(), 1):
                scores[inn] = scores.get(inn, 0) + 1 / (60 + rank)
                positions.setdefault(inn, position)
        categories = requested_categories(context)
        coverage = supplier_category_coverage(self.cards, categories)
        for position in np.argsort(-dense, kind="stable"):
            card = self.cards[position]
            inn = card["supplier_inn"]
            if card["category"] in categories:
                scores.setdefault(inn, 0.0)
                if self.cards[positions.get(inn, int(position))]["category"] not in categories:
                    positions[inn] = int(position)
                positions.setdefault(inn, int(position))
        selected = sorted(
            scores,
            key=lambda inn: (
                -coverage.get(inn, 0),
                -scores[inn],
                -dense[positions[inn]] if categories else 0.0,
                -lexical[positions[inn]] if categories else 0.0,
                inn,
            ),
        )[:limit]
        reasons: dict[str, list[str]] = {}
        if self.ranker is not None:
            selected, positions, scores, reasons = self.ranker.rank(
                text, self.cards, dense, lexical, scores, dense_order, lexical_order, context
            )
            selected = selected[:limit]
        return [
            self._metadata(
                SupplierCandidate(
                    inn=inn,
                    category=self.cards[positions[inn]]["category"],
                    profile=self.cards[positions[inn]]["profile_text"],
                    score=scores[inn],
                    similarity=float(dense[positions[inn]]),
                    ranking_reasons=reasons.get(inn, []),
                    matched_category_count=coverage.get(inn, 0),
                )
            )
            for inn in selected
        ]
