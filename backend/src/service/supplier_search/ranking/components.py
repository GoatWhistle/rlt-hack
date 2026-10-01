from collections.abc import Sequence

from src.models.candidate import ProductMatch
from src.models.enums import MatchBasis
from src.models.purchase import PurchaseSummary
from src.models.scoring import Score

BASIS_WEIGHTS = {
    MatchBasis.STOCK: 1.0,
    MatchBasis.CATALOG: 0.7,
    MatchBasis.INFERRED: 0.2,
}
SIMILAR_HALF_SATURATION = 5.0
WINS_HALF_SATURATION = 2.0


def coverage_score(matches: Sequence[ProductMatch], total_items: int) -> Score:
    return Score.ratio(len({match.item_id for match in matches}), total_items)


def evidence_score(matches: Sequence[ProductMatch]) -> Score:
    if not matches:
        return Score.zero()
    return Score.clamp(sum(BASIS_WEIGHTS[match.basis] for match in matches) / len(matches))


def _saturation(count: int, half: float) -> float:
    return count / (count + half)


def history_score(history: PurchaseSummary) -> Score:
    similar = _saturation(history.similar, SIMILAR_HALF_SATURATION)
    wins = _saturation(history.wins, WINS_HALF_SATURATION)
    return Score.clamp((similar + wins) / 2)
