import pytest

from src.models.embedding import OfferSearchHit
from src.models.search import SearchFilters
from src.service.catalog_search.service import CatalogSearch
from src.service.errors import ServiceError


class Encoder:
    model_key = "4b"
    dimensions = 2

    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors

    async def encode(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        assert query
        return self.vectors


class Index:
    async def search_filtered(
        self, vector: list[float], model_key: str, limit: int, filters: SearchFilters
    ) -> list[OfferSearchHit]:
        assert vector == [1.0, 0.0]
        assert model_key == "4b"
        assert limit == 10
        assert filters.regions == ("78",)
        assert filters.item_type == "goods"
        return []


async def test_catalog_vector_validation_and_filters() -> None:
    service = CatalogSearch(Index(), Encoder([[1.0, 0.0]]))
    assert await service.search("paper", 10, ["78"], "goods") == []
    with pytest.raises(ServiceError):
        await service.search(" ", 10, [], None)


@pytest.mark.parametrize("vectors", [[], [[0.0, 0.0]], [[float("nan"), 1.0]], [[1.0]]])
async def test_invalid_catalog_vectors(vectors: list[list[float]]) -> None:
    with pytest.raises(ServiceError):
        await CatalogSearch(Index(), Encoder(vectors)).search("paper", 10, [], None)
