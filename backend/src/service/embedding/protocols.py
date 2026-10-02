from typing import Protocol

from src.models.ranking.embedding import EmbeddingDocument, OfferSearchHit


class TextEmbedder(Protocol):
    model_key: str
    dimensions: int

    async def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]: ...


class EmbeddingRepository(Protocol):
    async def pending(
        self, model_key: str, dimensions: int, limit: int
    ) -> list[EmbeddingDocument]: ...

    async def save(
        self, documents: list[EmbeddingDocument], vectors: list[list[float]], model_key: str
    ) -> None: ...

    async def search(
        self, vector: list[float], model_key: str, limit: int
    ) -> list[OfferSearchHit]: ...
