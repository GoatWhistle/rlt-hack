from dataclasses import replace
from uuid import UUID

import pytest

from src.adapter.repository.clickhouse.history_search.retriever import ClickHouseHistoryRetriever
from src.adapter.repository.clickhouse.offer_search.retriever import ClickHouseLexicalRetriever
from src.adapter.repository.clickhouse.participation.history import ClickHousePurchaseHistory
from src.adapter.text.analyzer.analyzer import RussianAnalyzer
from src.models.enums import Availability, ItemType, PurchaseOutcome, VerificationStatus
from src.models.offer import Offer
from src.models.purchase import PurchaseRecord, PurchaseSummary
from src.models.query_item import SearchRequest
from src.models.search import SearchFilters, SearchQuery, SearchText
from tests.adapter.repository.seed import Seeder
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.fakes.domain import make_item, make_offer, make_source, make_supplier
from tests.fakes.domain import make_request as build_request

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb

ALPHA = make_supplier("alpha", inn="7801234567")
BETA = make_supplier("beta", inn="7807654321")
GAMMA = replace(make_supplier("gamma", inn="4701234567"), region="47")
ITEMS = (make_item("i1", "крупа гречневая ядрица"), make_item("i2", "рис"))


def named(
    key: str,
    name: str,
    supplier_id: UUID | None = ALPHA.supplier_id,
    availability: Availability = Availability.AVAILABLE,
) -> Offer:
    offer = make_offer(key, supplier=ALPHA)
    return replace(offer, name=name, supplier_id=supplier_id, availability=availability)


def request(regions: tuple[str, ...] = (), item_type: ItemType | None = None) -> SearchRequest:
    filters = SearchFilters(regions=regions, item_type=item_type)
    return build_request(*ITEMS, query=SearchQuery(SearchText("крупа; рис"), filters=filters))


async def seed_offers(gateway: ChdbGateway) -> dict[str, Offer]:
    offers = {
        "buckwheat": named("buckwheat", "Крупа гречневая ядрица 1 сорт"),
        "rice": named("rice", "Рис шлифованный круглый"),
        "gamma": named("gamma", "Гречневая крупа продел", supplier_id=GAMMA.supplier_id),
        "gone": named(
            "gone",
            "Крупа гречневая ядрица",
            supplier_id=BETA.supplier_id,
            availability=Availability.UNAVAILABLE,
        ),
        "orphan": replace(
            named("orphan", "Крупа гречневая ядрица", supplier_id=None),
            seller_status=VerificationStatus.UNVERIFIED,
        ),
    }
    seeder = Seeder(gateway)
    await seeder.suppliers(ALPHA, BETA, GAMMA)
    await seeder.sources(make_source())
    await seeder.offers(*offers.values())
    return offers


async def test_lexical_channel_ranks_suppliers_by_matched_items(gateway: ChdbGateway) -> None:
    offers = await seed_offers(gateway)
    retriever = ClickHouseLexicalRetriever(gateway, RussianAnalyzer())
    hits = await retriever.retrieve(request(), 10)
    assert retriever.channel == hits.channel == "lexical"
    assert [hit.supplier_id for hit in hits.hits] == [ALPHA.supplier_id, GAMMA.supplier_id]
    alpha_items = {item.item_id: item.offer_ids for item in hits.hits[0].items}
    assert alpha_items == {
        "i1": (offers["buckwheat"].offer_id,),
        "i2": (offers["rice"].offer_id,),
    }
    assert hits.hits[1].items[0].offer_ids == (offers["gamma"].offer_id,)
    assert len((await retriever.retrieve(request(), 1)).hits) == 1


async def test_lexical_channel_respects_regions_and_item_type(gateway: ChdbGateway) -> None:
    offers = await seed_offers(gateway)
    await Seeder(gateway).offers(replace(offers["rice"], delivery_regions=("47",)))
    retriever = ClickHouseLexicalRetriever(gateway, RussianAnalyzer())
    regional = await retriever.retrieve(request(regions=("47",)), 10)
    assert {hit.supplier_id for hit in regional.hits} == {ALPHA.supplier_id, GAMMA.supplier_id}
    alpha = next(hit for hit in regional.hits if hit.supplier_id == ALPHA.supplier_id)
    assert alpha.item_ids == frozenset({"i2"})
    services = await retriever.retrieve(request(item_type=ItemType.SERVICE), 10)
    assert services.hits == ()
    goods = await retriever.retrieve(request(item_type=ItemType.GOODS), 10)
    assert len(goods.hits) == 2


async def test_lexical_channel_skips_items_without_needles(gateway: ChdbGateway) -> None:
    await seed_offers(gateway)
    retriever = ClickHouseLexicalRetriever(gateway, RussianAnalyzer())
    short = build_request(make_item("i1", "ab"))
    assert (await retriever.retrieve(short, 10)).hits == ()


async def seed_history(gateway: ChdbGateway) -> None:
    seeder = Seeder(gateway)
    await seeder.suppliers(ALPHA, GAMMA)
    await seeder.lot("L1", "Поставка крупы гречневой")
    await seeder.lot("L2", "Продукты питания", ("Рис длиннозерный", "Соль"))
    await seeder.lot("L3", "Поставка бумаги офисной")
    await seeder.participation("L1", ALPHA, won=True)
    await seeder.participation("L1", GAMMA, won=False)
    await seeder.participation("L2", GAMMA, won=True)
    await seeder.participation("L3", ALPHA, won=True)


async def test_history_channel_weights_wins(gateway: ChdbGateway) -> None:
    await seed_history(gateway)
    retriever = ClickHouseHistoryRetriever(gateway, RussianAnalyzer())
    hits = await retriever.retrieve(request(), 10)
    assert retriever.channel == hits.channel == "history"
    by_supplier = {hit.supplier_id: {item.item_id: item for item in hit.items} for hit in hits.hits}
    assert set(by_supplier) == {ALPHA.supplier_id, GAMMA.supplier_id}
    alpha_i1 = by_supplier[ALPHA.supplier_id]["i1"]
    gamma_i1 = by_supplier[GAMMA.supplier_id]["i1"]
    assert alpha_i1.lot_ids == ("L1",)
    assert alpha_i1.relevance == pytest.approx(2 * gamma_i1.relevance)
    assert by_supplier[GAMMA.supplier_id]["i2"].lot_ids == ("L2",)
    regional = await retriever.retrieve(request(regions=("47",)), 10)
    assert [hit.supplier_id for hit in regional.hits] == [GAMMA.supplier_id]
    short = build_request(make_item("i1", "ab"))
    assert (await retriever.retrieve(short, 10)).hits == ()


async def test_purchase_history_counts_similar_lots(gateway: ChdbGateway) -> None:
    await seed_history(gateway)
    history = ClickHousePurchaseHistory(gateway, RussianAnalyzer())
    summaries = await history.summarize([ALPHA.supplier_id, GAMMA.supplier_id], ITEMS, 1)
    assert summaries[ALPHA.supplier_id] == PurchaseSummary(
        similar=1,
        wins=1,
        records=(
            PurchaseRecord("L1", "Поставка крупы гречневой", PurchaseOutcome.WINNER, ("i1",)),
        ),
    )
    gamma = summaries[GAMMA.supplier_id]
    assert (gamma.similar, gamma.wins) == (2, 1)
    assert gamma.records == (
        PurchaseRecord("L2", "Продукты питания", PurchaseOutcome.WINNER, ("i2",)),
    )
    assert await history.summarize([], ITEMS, 1) == {}
    assert await history.summarize([ALPHA.supplier_id], (make_item("i1", "ab"),), 1) == {}
