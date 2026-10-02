from collections import defaultdict
from datetime import date
from typing import Any, cast

import numpy as np

from src.adapter.repository.ranker.features import FEATURES
from src.adapter.repository.ranker.model import CandidateRanker
from src.models.search.search_context import SearchContext


class Model:
    def predict(self, rows: np.ndarray, *, thread_count: int) -> np.ndarray:
        self.rows = rows
        return rows[:, 0]

    def get_feature_importance(self, pool: Any, *, type: str, thread_count: int) -> np.ndarray:
        return np.zeros((pool.num_row(), len(FEATURES) + 1))


def make_ranker(tmp_path: Any, cards: list[dict[str, Any]]) -> Any:
    ranker = cast(Any, CandidateRanker(tmp_path))
    ranker.model = Model()
    ranker.suppliers = {}
    ranker.categories = {}
    ranker.customers = {}
    ranker.by_customer = defaultdict(list)
    ranker.cutoff = date(2025, 1, 1)
    ranker.positions = defaultdict(list)
    for index, card in enumerate(cards):
        ranker.positions[card["supplier_inn"]].append(index)
    return ranker


def test_category_pool_uses_relevance_instead_of_inn_for_zero_rrf(tmp_path: Any) -> None:
    cards = [
        {"supplier_inn": f"{number:03}", "category": "17.12", "profile_text": "paper"}
        for number in range(250)
    ]
    ranker = make_ranker(tmp_path, cards)
    dense = np.linspace(0.0, 1.0, len(cards))
    ordered, positions, scores, reasons = ranker.rank(
        "paper",
        cards,
        dense,
        np.zeros(len(cards)),
        {card["supplier_inn"]: 0.0 for card in cards},
        {},
        {},
        SearchContext(okpd2_codes=("17.12.14.110",)),
    )
    assert len(ordered) == 200
    assert ordered[0] == "249"
    assert "000" not in ordered
    assert positions["249"] == 249
    assert scores["249"] == 1.0
    assert reasons["249"] == []
    assert ranker.model.rows.shape == (200, len(FEATURES))
    assert np.isnan(ranker.model.rows[:, FEATURES.index("price_distance")]).all()
    assert (ranker.model.rows[:, FEATURES.index("missing_customer")] == 1).all()
    assert (ranker.model.rows[:, FEATURES.index("missing_price")] == 1).all()


def test_category_coverage_precedes_score_and_selects_matching_profile(tmp_path: Any) -> None:
    cards = [
        {"supplier_inn": "multi", "category": "01.11", "profile_text": "paper"},
        {"supplier_inn": "multi", "category": "17.12", "profile_text": "paper"},
        {"supplier_inn": "multi", "category": "28.13", "profile_text": "pump"},
        {"supplier_inn": "single", "category": "17.12", "profile_text": "paper"},
        {"supplier_inn": "other", "category": "01.11", "profile_text": "paper"},
    ]
    ranker = make_ranker(tmp_path, cards)
    ordered, positions, _, _ = ranker.rank(
        "paper pump",
        cards,
        np.asarray([1.0, 0.1, 0.2, 0.8, 0.99]),
        np.zeros(5),
        {"multi": 0.001, "single": 0.1, "other": 0.2},
        {"multi": 0, "single": 3, "other": 4},
        {},
        SearchContext(okpd2_codes=("17.12.14", "28.13.11")),
    )
    assert ordered == ["multi", "single", "other"]
    assert positions["multi"] == 2


def test_empty_candidate_pool_does_not_call_model(tmp_path: Any) -> None:
    ranker = make_ranker(tmp_path, [])
    assert ranker.rank("paper", [], np.asarray([]), np.asarray([]), {}, {}, {}) == (
        [],
        {},
        {},
        {},
    )
    assert not hasattr(ranker.model, "rows")
