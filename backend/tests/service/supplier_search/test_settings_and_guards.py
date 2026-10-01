from collections.abc import Callable

import pytest

from src.models.retrieval import ChannelHit, RetrievalHits
from src.service.supplier_search.enrichment.loader import EnrichmentLoader
from src.service.supplier_search.fusion.rrf import ReciprocalRankFusion
from src.service.supplier_search.retrieval.runner import ChannelRunner
from src.service.supplier_search.settings import ScoreWeights, SearchSettings
from tests.fakes.domain import make_item, make_supplier
from tests.fakes.drafts import make_draft
from tests.fakes.ports import FakeDirectory, FakeHistory, FakeOfferCatalog


@pytest.mark.parametrize(
    "build",
    [
        lambda: SearchSettings(timeout_seconds=0),
        lambda: SearchSettings(retrieval_depth_factor=0),
        lambda: SearchSettings(rrf_k=0),
        lambda: SearchSettings(coverage_threshold=0),
        lambda: SearchSettings(coverage_threshold=1.1),
    ],
)
def test_settings_reject_impossible_values(build: Callable[[], SearchSettings]) -> None:
    with pytest.raises(ValueError, match="must"):
        build()


def test_weights_must_not_all_be_zero_or_negative() -> None:
    with pytest.raises(ValueError, match="weights"):
        ScoreWeights(0, 0, 0, 0)
    with pytest.raises(ValueError, match="weights"):
        ScoreWeights(fusion=-1)
    assert ScoreWeights().total == pytest.approx(1.0)
    assert SearchSettings().retrieval_depth(20) == 60


def test_draft_needs_requested_items() -> None:
    with pytest.raises(ValueError, match="item"):
        make_draft(total_items=0)


def test_runner_needs_a_channel() -> None:
    with pytest.raises(ValueError, match="channel"):
        ChannelRunner(())


async def test_loader_skips_offer_lookup_without_offers() -> None:
    supplier = make_supplier()
    catalog = FakeOfferCatalog()
    loader = EnrichmentLoader(FakeDirectory((supplier,)), catalog, FakeHistory(), SearchSettings())
    fused = ReciprocalRankFusion().fuse(
        (RetrievalHits("lexical", (ChannelHit(supplier.supplier_id, 1),)),)
    )
    enrichment, warnings = await loader.load(fused, (make_item(),))
    assert enrichment.suppliers == {supplier.supplier_id: supplier}
    assert (warnings, catalog.lookups) == ((), [])
