import asyncio
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from catboost import CatBoostRanker, Pool

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.repository.ranker.features import FEATURES
from src.adapter.repository.ranker.model import CandidateRanker


async def main():
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        values = np.random.default_rng(42).normal(size=(20, len(FEATURES)))
        model = CatBoostRanker(
            iterations=3,
            depth=2,
            loss_function="QuerySoftMax",
            verbose=False,
            allow_writing_files=False,
            thread_count=1,
        )
        model.fit(
            Pool(
                values,
                [0, 1] * 10,
                group_id=np.repeat(np.arange(10), 2),
                feature_names=list(FEATURES),
            )
        )
        model.save_model(str(root / "ranker.cbm"))
        pq.write_table(
            pa.Table.from_pylist([{"supplier_inn": "a", "participations": 4, "wins": 2}]),
            root / "supplier_stats.parquet",
        )
        pq.write_table(
            pa.Table.from_pylist(
                [{"supplier_inn": "a", "category": "paper", "participations": 4.0, "wins": 2.0}]
            ),
            root / "category_stats.parquet",
        )
        manifest = {
            "features": list(FEATURES),
            "cards_sha256": "cards",
            "model": "Qwen/Qwen3-Embedding-4B",
            "history_before": "2024-12-01",
            "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()},
        }
        (root / "runtime.json").write_text(json.dumps(manifest))
        cards = [
            {"supplier_inn": "a", "category": "paper", "profile_text": "office paper"},
            {"supplier_inn": "b", "category": "paper", "profile_text": "white paper"},
        ]
        ranker = CandidateRanker(root)
        await ranker.initialize(cards, "cards")
        selected, positions, scores, reasons = await asyncio.to_thread(
            ranker.rank,
            "paper",
            cards,
            np.array([0.9, 0.8]),
            np.array([1.0, 2.0]),
            {"a": 0.03, "b": 0.02},
            {"a": 0, "b": 1},
            {"b": 1, "a": 0},
        )
        assert set(selected) == {"a", "b"} and positions == {"a": 0, "b": 1}
        assert all(np.isfinite(list(scores.values())))
        assert set(reasons) == {"a", "b"}
        assert all(
            set(value) <= {"relevance", "experience", "category", "recency"}
            for value in reasons.values()
        )
        try:
            await ranker.initialize(cards, "other-cards")
            raise AssertionError("Mismatched index accepted")
        except ValueError:
            pass
        (root / "ranker.cbm").write_bytes(b"corrupt")
        try:
            await ranker.initialize(cards, "cards")
            raise AssertionError("Corrupted model accepted")
        except ValueError:
            pass
    print("Ranker artifact integrity, feature schema and inference: OK")


asyncio.run(main())
