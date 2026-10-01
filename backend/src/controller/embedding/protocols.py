from typing import Protocol

from src.models.embedding import OfferSearchHit


class OfferEmbedding(Protocol):
    async def run_once(self, batch_size: int, max_batches: int) -> int: ...

    async def run_forever(self, batch_size: int, interval: float) -> None: ...

    async def search(self, text: str, limit: int) -> list[OfferSearchHit]: ...
