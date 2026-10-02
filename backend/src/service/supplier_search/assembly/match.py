from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

from src.models.candidate import ProductMatch
from src.models.enums import MatchBasis, RequirementStatus
from src.models.offer_evidence import OfferEvidence
from src.models.offer_snapshot import OfferSnapshot
from src.models.query_item import QueryItem
from src.models.requirement import RequirementCheck, check_requirements

DESCRIPTION_LIMIT = 500


def is_stock(card: OfferEvidence) -> bool:
    return card.is_current and card.backs_supplier and card.in_stock and card.evidence is not None


def is_catalog(card: OfferEvidence) -> bool:
    return card.catalog_confirmed and card.backs_supplier and card.evidence is not None


def _freshness(card: OfferEvidence) -> tuple[bool, datetime, str]:
    return (card.is_current, card.offer.last_seen_at, str(card.offer.offer_id))


def offer_texts(card: OfferEvidence) -> tuple[str, ...]:
    offer = card.offer
    return (
        offer.name,
        offer.article,
        " ".join(f"{key} {value}" for key, value in offer.attributes.items()),
        offer.description[:DESCRIPTION_LIMIT],
    )


def _conflicts(checks: Sequence[RequirementCheck]) -> bool:
    return any(check.status == RequirementStatus.CONFLICT for check in checks)


class MatchResolver:
    def resolve(
        self, item: QueryItem, cards: Sequence[OfferEvidence], signalled: bool
    ) -> ProductMatch | None:
        checks = {
            card.offer.offer_id: check_requirements(item.requirements, offer_texts(card))
            for card in cards
        }
        clean = [card for card in cards if not _conflicts(checks[card.offer.offer_id])]
        stock = [card for card in clean if is_stock(card)]
        if stock:
            return _backed(item, MatchBasis.STOCK, stock, checks)
        catalog = [card for card in clean if is_catalog(card)]
        if catalog:
            return _backed(item, MatchBasis.CATALOG, catalog, checks)
        evidenced = [card for card in clean if card.evidence is not None]
        if evidenced:
            return _backed(item, MatchBasis.INFERRED, evidenced, checks)
        conflicting = [card for card in cards if card.evidence is not None]
        if conflicting:
            return _backed(item, MatchBasis.INFERRED, conflicting, checks)
        if cards or signalled:
            return ProductMatch(item_id=item.item_id, basis=MatchBasis.INFERRED)
        return None


def _backed(
    item: QueryItem,
    basis: MatchBasis,
    cards: Sequence[OfferEvidence],
    checks: Mapping[UUID, tuple[RequirementCheck, ...]],
) -> ProductMatch:
    best = max(cards, key=_freshness)
    return ProductMatch(
        item_id=item.item_id,
        basis=basis,
        offer_id=best.offer.offer_id,
        evidence=best.evidence,
        offer=OfferSnapshot.of(best),
        checks=checks[best.offer.offer_id],
    )
