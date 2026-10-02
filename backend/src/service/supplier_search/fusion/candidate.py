from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import UUID

from src.models.ranking.scoring import ChannelRank, Score


@dataclass(frozen=True, slots=True)
class ItemRefs:
    offer_ids: tuple[UUID, ...] = ()
    lot_ids: tuple[str, ...] = ()
    inferred_offer_ids: tuple[UUID, ...] = ()

    def merge(
        self, offer_ids: tuple[UUID, ...], lot_ids: tuple[str, ...], *, inferred: bool = False
    ) -> "ItemRefs":
        uncertain = set(self.inferred_offer_ids)
        if inferred:
            uncertain.update(set(offer_ids) - (set(self.offer_ids) - uncertain))
        else:
            uncertain.difference_update(offer_ids)
        return ItemRefs(
            inferred_offer_ids=tuple(sorted(uncertain, key=str)),
            offer_ids=tuple(dict.fromkeys((*self.offer_ids, *offer_ids))),
            lot_ids=tuple(dict.fromkeys((*self.lot_ids, *lot_ids))),
        )


@dataclass(frozen=True, slots=True)
class FusedCandidate:
    supplier_id: UUID
    fusion: Score
    channels: tuple[ChannelRank, ...] = ()
    items: Mapping[str, ItemRefs] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", MappingProxyType(dict(self.items)))

    @property
    def offer_ids(self) -> tuple[UUID, ...]:
        return tuple(
            dict.fromkeys(offer_id for refs in self.items.values() for offer_id in refs.offer_ids)
        )
