from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from src.models.enums import RetrievalChannel
from src.models.retrieval import ChannelHit, RetrievalHits
from src.models.scoring import ChannelRank, Score
from src.service.supplier_search.fusion.candidate import FusedCandidate, ItemRefs


@dataclass(slots=True)
class _Accumulator:
    supplier_id: UUID
    raw: float = 0.0
    channels: list[ChannelRank] = field(default_factory=list)
    items: dict[str, ItemRefs] = field(default_factory=dict)

    def add(self, channel: str, hit: ChannelHit, k: int) -> None:
        self.raw += 1.0 / (k + hit.rank)
        self.channels.append(ChannelRank(channel, hit.rank))
        for item in hit.items:
            refs = self.items.get(item.item_id, ItemRefs())
            self.items[item.item_id] = refs.merge(
                item.offer_ids, item.lot_ids, inferred=channel == RetrievalChannel.CATALOG_VECTOR
            )


class ReciprocalRankFusion:
    def __init__(self, k: int = 60) -> None:
        if k < 1:
            raise ValueError("rrf k must be positive")
        self._k = k

    def fuse(self, results: Sequence[RetrievalHits]) -> tuple[FusedCandidate, ...]:
        accumulated: dict[UUID, _Accumulator] = {}
        for result in results:
            for hit in result.hits:
                entry = accumulated.setdefault(hit.supplier_id, _Accumulator(hit.supplier_id))
                entry.add(result.channel, hit, self._k)
        ceiling = len(results) / (self._k + 1)
        fused = [
            FusedCandidate(
                supplier_id=entry.supplier_id,
                fusion=Score.ratio(entry.raw, ceiling),
                channels=tuple(entry.channels),
                items=entry.items,
            )
            for entry in accumulated.values()
        ]
        fused.sort(key=lambda candidate: (-candidate.fusion.value, str(candidate.supplier_id)))
        return tuple(fused)
