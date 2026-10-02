from collections.abc import Sequence

from src.models.catalog.supplier import Supplier
from src.models.company.offer_evidence import OfferEvidence
from src.models.company.purchase import PurchaseSummary
from src.models.enums import HighlightCode, MatchBasis, VerificationStatus
from src.models.search.candidate import Highlight, ProductMatch


def _priced(matches: Sequence[ProductMatch], cards: Sequence[OfferEvidence]) -> int:
    priced = {card.offer.offer_id for card in cards if card.offer.price is not None}
    return sum(
        1 for match in matches if match.offer_id in priced and match.basis != MatchBasis.INFERRED
    )


class HighlightComposer:
    def compose(
        self,
        supplier: Supplier,
        matches: Sequence[ProductMatch],
        cards: Sequence[OfferEvidence],
        history: PurchaseSummary,
        total_items: int,
    ) -> tuple[Highlight, ...]:
        stock = sum(1 for match in matches if match.basis == MatchBasis.STOCK)
        counters = (
            (HighlightCode.IN_STOCK, stock),
            (HighlightCode.HAS_PRICE, _priced(matches, cards)),
            (HighlightCode.PAST_WINS, history.wins),
            (HighlightCode.SIMILAR_PURCHASES, history.similar),
        )
        highlights: list[Highlight] = []
        confirmed = sum(match.basis != MatchBasis.INFERRED for match in matches)
        if confirmed:
            coverage = {"matched": confirmed, "total": total_items}
            highlights.append(Highlight(HighlightCode.COVERS_ITEMS, coverage))
        highlights.extend(
            Highlight(code, {"count": count}) for code, count in counters if count > 0
        )
        if supplier.identity_status == VerificationStatus.VERIFIED and supplier.has_valid_inn:
            highlights.append(Highlight(HighlightCode.VERIFIED_IDENTITY))
        return tuple(highlights)
