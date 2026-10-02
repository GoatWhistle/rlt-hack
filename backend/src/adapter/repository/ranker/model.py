import asyncio
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from catboost import CatBoostRanker, Pool

from src.adapter.repository.ranker.features import FEATURES, feature_row
from src.adapter.repository.supplier_index.category_priority import (
    requested_categories,
    supplier_category_coverage,
)
from src.models.search.search_context import SearchContext


class CandidateRanker:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    async def initialize(self, cards: list[dict], cards_checksum: str) -> None:
        await asyncio.to_thread(self._load, cards, cards_checksum)

    def _load(self, cards: list[dict], cards_checksum: str) -> None:
        manifest = json.loads((self.directory / "runtime.json").read_text())
        if manifest["features"] != list(FEATURES) or manifest["cards_sha256"] != cards_checksum:
            raise ValueError("Ranker feature or card schema mismatch")
        if manifest["model"] != "Qwen/Qwen3-Embedding-4B":
            raise ValueError("Only the evaluated 4B ranker is supported")
        required = {"ranker.cbm", "supplier_stats.parquet", "category_stats.parquet"}
        if not required <= set(manifest["files"]) or set(manifest["files"]) - required - {
            "customer_stats.parquet"
        }:
            raise ValueError("Incomplete ranker artifact manifest")
        for name, expected in manifest["files"].items():
            if name not in {
                "ranker.cbm",
                "supplier_stats.parquet",
                "category_stats.parquet",
                "customer_stats.parquet",
            }:
                raise ValueError("Unexpected ranker artifact")
            with (self.directory / name).open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                    raise ValueError("Ranker checksum mismatch")
        self.model = CatBoostRanker()
        self.model.load_model(str(self.directory / "ranker.cbm"))
        if self.model.feature_names_ != list(FEATURES):
            raise ValueError("Ranker model feature names mismatch")
        self.version = (
            manifest["files"]["ranker.cbm"]
            + "/context-v1/"
            + manifest["files"].get("customer_stats.parquet", "none")
        )
        self.cutoff = date.fromisoformat(manifest["history_before"])
        self.suppliers = {
            row["supplier_inn"]: row
            for row in pq.read_table(self.directory / "supplier_stats.parquet").to_pylist()
        }
        self.categories = {
            (row["supplier_inn"], row["category"]): row
            for row in pq.read_table(self.directory / "category_stats.parquet").to_pylist()
        }
        self.customers = {}
        self.by_customer = defaultdict(list)
        if "customer_stats.parquet" in manifest["files"]:
            for row in pq.read_table(self.directory / "customer_stats.parquet").to_pylist():
                self.customers[(row["supplier_inn"], row["customer_inn"])] = row
                self.by_customer[row["customer_inn"]].append(row)
            for entries in self.by_customer.values():
                entries.sort(
                    key=lambda row: (-row["wins"], -row["participations"], row["supplier_inn"])
                )
        self.positions = defaultdict(list)
        for i, card in enumerate(cards):
            self.positions[card["supplier_inn"]].append(i)

    def rank(
        self,
        text,
        cards,
        dense,
        lexical,
        scores,
        dense_order,
        lexical_order,
        context: SearchContext | None = None,
    ):
        context = context or SearchContext()
        customer_order = [
            row["supplier_inn"]
            for row in self.by_customer.get(context.customer_inn, [])
            if row["supplier_inn"] in self.positions
        ][:100]
        scores = dict(scores)
        for rank, inn in enumerate(customer_order, 1):
            scores[inn] = scores.get(inn, 0) + 0.5 / (60 + rank)
        categories = requested_categories(context)
        coverage = supplier_category_coverage(cards, categories)
        best_positions = {}
        for inn in scores:
            options = self.positions[inn]
            matching = [index for index in options if cards[index]["category"] in categories]
            candidates = matching or options
            best_positions[inn] = (
                max(candidates, key=lambda index: (dense[index], lexical[index], -index))
                if matching or inn not in dense_order
                else dense_order[inn]
            )
        selected = sorted(
            scores,
            key=lambda inn: (
                -coverage.get(inn, 0),
                -scores[inn],
                -dense[best_positions[inn]] if categories else 0.0,
                -lexical[best_positions[inn]] if categories else 0.0,
                inn,
            ),
        )[:200]
        if not selected:
            return [], {}, {}, {}
        ranks = [
            {inn: rank for rank, inn in enumerate(order, 1)}
            for order in (dense_order, lexical_order, customer_order)
        ]
        rows, positions = [], {}
        for inn in selected:
            options = self.positions[inn]
            position = best_positions[inn]
            positions[inn] = position
            card = cards[position]
            raw = [
                dense[position],
                lexical[position],
                scores[inn],
                ranks[0].get(inn, 301),
                ranks[1].get(inn, 301),
                ranks[2].get(inn, 301),
            ]
            rows.append(
                feature_row(
                    {
                        "query_text": text,
                        "customer_inn": context.customer_inn,
                        "start_price": context.start_price,
                    },
                    card,
                    self.suppliers.get(inn, {}),
                    self.categories.get((inn, card["category"]), {}),
                    self.customers.get((inn, context.customer_inn), {}),
                    raw,
                    self.cutoff,
                    len(options),
                )
            )
        predicted = self.model.predict(np.asarray(rows), thread_count=2)
        if not np.isfinite(predicted).all():
            raise ValueError("Invalid ranker scores")
        model_scores = dict(zip(selected, predicted.tolist(), strict=True))
        ordered = sorted(selected, key=lambda inn: (-coverage.get(inn, 0), -model_scores[inn], inn))
        top = ordered[:100]
        lookup = {inn: row for inn, row in zip(selected, rows, strict=True)}
        shap = self.model.get_feature_importance(
            Pool([lookup[inn] for inn in top], feature_names=list(FEATURES)),
            type="ShapValues",
            thread_count=2,
        )
        reasons = {}
        for inn, contributions in zip(top, shap, strict=True):
            values = lookup[inn]
            groups = {
                "relevance": float(sum(contributions[:7])),
                "experience": float(sum(contributions[7:10])) if values[7] > 0 else 0,
                "category": float(sum(contributions[10:13])) if values[10] > 0 else 0,
                "customer": float(sum(contributions[13:16])) if values[13] > 0 else 0,
                "price": float(contributions[18]) if context.start_price is not None else 0,
                "recency": float(contributions[17])
                if cards[positions[inn]].get("profile_last_date")
                else 0,
            }
            reasons[inn] = [
                key for key in sorted(groups, key=groups.get, reverse=True) if groups[key] > 1e-6
            ][:3]
        return ordered, positions, model_scores, reasons
