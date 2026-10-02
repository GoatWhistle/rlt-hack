from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from src.models.company.offer_evidence import OfferEvidence
from src.models.enums import MatchBasis
from src.models.search.candidate import ProductMatch


def is_stock(card: OfferEvidence) -> bool:
    return card.is_current and card.backs_supplier and card.in_stock and card.evidence is not None


def is_catalog(card: OfferEvidence) -> bool:
    return card.catalog_confirmed and card.backs_supplier and card.evidence is not None


def _freshness(card: OfferEvidence) -> tuple[bool, datetime, str]:
    return (card.is_current, card.offer.last_seen_at, str(card.offer.offer_id))


def _backed(item_id: str, basis: MatchBasis, cards: Sequence[OfferEvidence]) -> ProductMatch:
    best = max(cards, key=_freshness)
    return ProductMatch(
        item_id=item_id,
        basis=basis,
        offer_id=best.offer.offer_id,
        evidence=best.evidence,
    )


class MatchResolver:
    def resolve(
        self,
        item_id: str,
        cards: Sequence[OfferEvidence],
        signalled: bool,
        inferred_offer_ids: tuple[UUID, ...] = (),
    ) -> ProductMatch | None:
        grounded = [card for card in cards if card.offer.offer_id not in inferred_offer_ids]
        stock = [card for card in grounded if is_stock(card)]
        if stock:
            return _backed(item_id, MatchBasis.STOCK, stock)
        catalog = [card for card in grounded if is_catalog(card)]
        if catalog:
            return _backed(item_id, MatchBasis.CATALOG, catalog)
        evidenced = [card for card in cards if card.evidence is not None]
        if evidenced:
            return _backed(item_id, MatchBasis.INFERRED, evidenced)
        if cards or signalled:
            return ProductMatch(item_id=item_id, basis=MatchBasis.INFERRED)
        return None
