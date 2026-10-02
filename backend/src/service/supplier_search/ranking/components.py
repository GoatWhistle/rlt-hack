from collections.abc import Sequence

from src.models.company.purchase import PurchaseSummary
from src.models.enums import MatchBasis
from src.models.ranking.scoring import Score
from src.models.search.candidate import ProductMatch

BASIS_WEIGHTS = {
    MatchBasis.STOCK: 1.0,
    MatchBasis.CATALOG: 0.7,
    MatchBasis.INFERRED: 0.2,
}
SIMILAR_HALF_SATURATION = 5.0
WINS_HALF_SATURATION = 2.0


def coverage_score(matches: Sequence[ProductMatch], total_items: int) -> Score:
    confirmed = {match.item_id for match in matches if match.basis != MatchBasis.INFERRED}
    return Score.ratio(len(confirmed), total_items)


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
