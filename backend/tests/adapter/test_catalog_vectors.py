from uuid import UUID

import httpx
import pytest

from src.adapter.client.catalog_vectors.retriever import CatalogVectorRetriever
from src.adapter.client.errors import MlProtocolError, MlServiceError
from src.models.enums import RetrievalChannel
from src.models.query_item import QueryItem, SearchRequest
from src.models.search import SearchQuery, SearchText
from src.service.supplier_search.fusion.candidate import ItemRefs

SUPPLIER = UUID("00000000-0000-4000-8000-000000000001")
OFFER = UUID("00000000-0000-4000-8000-000000000002")


async def test_catalog_groups_offers_and_preserves_sources() -> None:
    async def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/catalog/search"
        return httpx.Response(
            200,
            json={
                "offers": [
                    {"offer_id": str(OFFER), "supplier_id": str(SUPPLIER), "similarity": 0.8},
                    {"offer_id": str(OFFER), "supplier_id": None, "similarity": 0.9},
                ]
            },
        )

    async with httpx.AsyncClient(
        base_url="http://test", transport=httpx.MockTransport(handle)
    ) as client:
        result = await CatalogVectorRetriever(client).retrieve(
            SearchRequest(SearchQuery(SearchText("paper")), (QueryItem("p", "paper"),)), 10
        )
    assert result.channel == RetrievalChannel.CATALOG_VECTOR
    assert len(result.hits) == 1
    assert result.hits[0].supplier_id == SUPPLIER
    assert result.hits[0].items[0].offer_ids == (OFFER,)


@pytest.mark.parametrize(
    ("status", "body", "error"), [(503, {}, MlServiceError), (200, {}, MlProtocolError)]
)
async def test_catalog_failures_are_explicit(
    status: int, body: dict[str, object], error: type[Exception]
) -> None:
    async with httpx.AsyncClient(
        base_url="http://test",
        transport=httpx.MockTransport(lambda request: httpx.Response(status, json=body)),
    ) as client:
        with pytest.raises(error):
            await CatalogVectorRetriever(client).retrieve(
                SearchRequest(SearchQuery(SearchText("paper")), (QueryItem("p", "paper"),)), 10
            )


def test_semantic_evidence_does_not_become_confirmation() -> None:
    refs = ItemRefs().merge((OFFER,), (), inferred=True)
    assert refs.inferred_offer_ids == (OFFER,)
    assert refs.merge((OFFER,), ()).inferred_offer_ids == ()
    assert (
        ItemRefs().merge((OFFER,), ()).merge((OFFER,), (), inferred=True).inferred_offer_ids == ()
    )
