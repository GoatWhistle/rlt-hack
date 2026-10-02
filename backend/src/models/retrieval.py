import math
from dataclasses import dataclass
from uuid import UUID

from src.models.errors import InvalidRankError


@dataclass(frozen=True, slots=True)
class ItemHit:
    item_id: str
    relevance: float
    offer_ids: tuple[UUID, ...] = ()
    lot_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.item_id:
            raise InvalidRankError("item hit has no item id")
        if not math.isfinite(self.relevance) or self.relevance < 0:
            raise InvalidRankError("relevance must be a finite non-negative number")


@dataclass(frozen=True, slots=True)
class ChannelHit:
    supplier_id: UUID
    rank: int
    items: tuple[ItemHit, ...] = ()

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise InvalidRankError("ranks start at 1")

    @property
    def item_ids(self) -> frozenset[str]:
        return frozenset(hit.item_id for hit in self.items)


@dataclass(frozen=True, slots=True)
class RetrievalHits:
    channel: str
    hits: tuple[ChannelHit, ...] = ()
    version: str = ""

    def __post_init__(self) -> None:
        if not self.channel:
            raise InvalidRankError("channel is empty")
        ranks = [hit.rank for hit in self.hits]
        if ranks != list(range(1, len(ranks) + 1)):
            raise InvalidRankError("channel ranks must run 1..n in order")
        suppliers = {hit.supplier_id for hit in self.hits}
        if len(suppliers) != len(self.hits):
            raise InvalidRankError("a supplier appears twice in one channel")
