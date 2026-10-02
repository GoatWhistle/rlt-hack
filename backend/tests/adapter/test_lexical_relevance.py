from dataclasses import replace

from src.adapter.repository.clickhouse.catalog.offer_search.retriever import (
    ClickHouseLexicalRetriever,
    OfferMatch,
)
from src.adapter.text.analyzer.analyzer import RussianAnalyzer
from src.models.enums import MatchBasis, RetrievalChannel
from src.models.ranking.retrieval import ChannelHit, ItemHit, RetrievalHits
from src.models.search.query_item import QueryItem
from src.service.supplier_search.assembly.match import MatchResolver
from src.service.supplier_search.fusion.rrf import ReciprocalRankFusion
from tests.fakes.domain import make_offer, make_offer_evidence, make_supplier


def test_description_and_short_prefix_do_not_confirm_water() -> None:
    supplier = make_supplier()
    names = ("Кроссовки", "Водолазка", "Водочный набор", "Игрушки для воды", "Вода")
    offers = [replace(make_offer(name, supplier=supplier), name=name) for name in names]
    pool = [
        OfferMatch(offer.offer_id, supplier.supplier_id, 10, (True,), offer.name)
        for offer in offers
    ]
    retriever = ClickHouseLexicalRetriever(None, RussianAnalyzer())
    hits = retriever._tally((QueryItem("water", "вода"),), (pool,)).hits("lexical", 10)
    item = hits.hits[0].items[0]
    assert set(item.offer_ids) == {offers[3].offer_id, offers[4].offer_id}
    assert item.inferred_offer_ids == (offers[3].offer_id,)


def test_weak_lexical_and_vector_signals_do_not_turn_stock_into_confirmation() -> None:
    supplier = make_supplier()
    offer = make_offer("Игрушки для воды", supplier=supplier)
    weak = ItemHit("water", 1.0, (offer.offer_id,), inferred_offer_ids=(offer.offer_id,))
    semantic = replace(weak, inferred_offer_ids=())
    channels = (
        RetrievalHits("lexical", (ChannelHit(supplier.supplier_id, 1, (weak,)),)),
        RetrievalHits(
            RetrievalChannel.CATALOG_VECTOR, (ChannelHit(supplier.supplier_id, 1, (semantic,)),)
        ),
    )
    for ordered in (channels, tuple(reversed(channels))):
        fused = ReciprocalRankFusion().fuse(ordered)[0]
        refs = fused.items["water"]
        assert refs.inferred_offer_ids == (offer.offer_id,)
        match = MatchResolver().resolve(
            "water", (make_offer_evidence(offer),), True, refs.inferred_offer_ids
        )
        assert match is not None
        assert match.basis == MatchBasis.INFERRED


def test_partial_multiword_title_is_not_a_confirmed_item() -> None:
    supplier = make_supplier()
    offer = make_offer("Бумага упаковочная", supplier=supplier)
    retriever = ClickHouseLexicalRetriever(None, RussianAnalyzer())
    pool = [OfferMatch(offer.offer_id, supplier.supplier_id, 10, (True, False), offer.name)]
    hits = retriever._tally((QueryItem("paper", "Бумага офисная"),), (pool,)).hits("lexical", 10)
    assert hits.hits[0].items[0].inferred_offer_ids == (offer.offer_id,)
