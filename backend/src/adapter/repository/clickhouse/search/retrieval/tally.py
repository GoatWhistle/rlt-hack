from dataclasses import dataclass, field
from uuid import UUID

from src.models.ranking.retrieval import ChannelHit, ItemHit, RetrievalHits

REFS_PER_ITEM = 5


@dataclass(slots=True)
class _ItemTally:
    relevance: float = 0.0
    offers: dict[UUID, float] = field(default_factory=dict)
    lots: dict[str, float] = field(default_factory=dict)
    inferred: set[UUID] = field(default_factory=set)


def _top[K](scores: dict[K, float], size: int) -> tuple[K, ...]:
    ordered = sorted(scores.items(), key=lambda entry: (-entry[1], str(entry[0])))
    return tuple(key for key, _ in ordered[:size])


class HitTally:
    def __init__(self, accumulate: bool, refs_per_item: int = REFS_PER_ITEM) -> None:
        self._accumulate = accumulate
        self._refs = refs_per_item
        self._suppliers: dict[UUID, dict[str, _ItemTally]] = {}

    def add_offer(
        self,
        supplier_id: UUID,
        item_id: str,
        offer_id: UUID,
        score: float,
        *,
        inferred: bool = False,
    ) -> None:
        tally = self._entry(supplier_id, item_id, score)
        if inferred and offer_id not in tally.offers:
            tally.inferred.add(offer_id)
        elif not inferred:
            tally.inferred.discard(offer_id)
        tally.offers[offer_id] = max(score, tally.offers.get(offer_id, 0.0))

    def add_lot(self, supplier_id: UUID, item_id: str, lot_id: str, score: float) -> None:
        tally = self._entry(supplier_id, item_id, score)
        tally.lots[lot_id] = max(score, tally.lots.get(lot_id, 0.0))

    def hits(self, channel: str, limit: int) -> RetrievalHits:
        totals = {
            supplier_id: sum(item.relevance for item in items.values())
            for supplier_id, items in self._suppliers.items()
        }
        ordered = sorted(totals, key=lambda key: (-totals[key], str(key)))[: max(limit, 0)]
        return RetrievalHits(
            channel,
            tuple(
                ChannelHit(supplier_id, rank, self._item_hits(supplier_id))
                for rank, supplier_id in enumerate(ordered, start=1)
            ),
        )

    def _entry(self, supplier_id: UUID, item_id: str, score: float) -> _ItemTally:
        items = self._suppliers.setdefault(supplier_id, {})
        tally = items.setdefault(item_id, _ItemTally())
        if self._accumulate:
            tally.relevance += score
        else:
            tally.relevance = max(tally.relevance, score)
        return tally

    def _item_hits(self, supplier_id: UUID) -> tuple[ItemHit, ...]:
        items = self._suppliers[supplier_id]
        return tuple(
            ItemHit(
                item_id=item_id,
                relevance=tally.relevance,
                offer_ids=_top(tally.offers, self._refs),
                lot_ids=_top(tally.lots, self._refs),
                inferred_offer_ids=tuple(
                    offer_id
                    for offer_id in _top(tally.offers, self._refs)
                    if offer_id in tally.inferred
                ),
            )
            for item_id, tally in sorted(items.items())
        )
