from dataclasses import replace
from datetime import timedelta

import pytest

from src.adapter.repository.clickhouse.offer_read.catalog import ClickHouseOfferCatalog
from src.adapter.repository.clickhouse.probe.probe import ClickHouseProbe
from src.adapter.repository.clickhouse.supplier_read.directory import ClickHouseSupplierDirectory
from src.adapter.repository.clickhouse.supplier_read.identity import ClickHouseSupplierIdentity
from src.models.enums import Availability, MatchStatus
from tests.adapter.repository.seed import Seeder
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.fakes.domain import CHECKED, make_offer, make_source, make_supplier, uid

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb

ALPHA = make_supplier("alpha", inn="7801234564")
BETA = make_supplier("beta", inn=None)
TWIN = make_supplier("twin", inn="7801234564")
GAMMA = make_supplier("gamma", inn="780123456724")


async def test_directory_reads_suppliers_by_id(gateway: ChdbGateway) -> None:
    await Seeder(gateway).suppliers(ALPHA, BETA)
    directory = ClickHouseSupplierDirectory(gateway)
    found = await directory.get_many([ALPHA.supplier_id, BETA.supplier_id, uid("ghost")])
    assert found == {ALPHA.supplier_id: ALPHA, BETA.supplier_id: BETA}
    assert await directory.get_many([]) == {}


async def test_directory_drops_catalog_operator_contacts(gateway: ChdbGateway) -> None:
    operator = replace(make_source(), base_url="https://www.productcenter.ru/")
    listed = replace(ALPHA, website="https://productcenter.ru/producers/1")
    seeder = Seeder(gateway)
    await seeder.sources(operator)
    await seeder.suppliers(listed)
    found = await ClickHouseSupplierDirectory(gateway).get_many([ALPHA.supplier_id])
    assert found[ALPHA.supplier_id].website == ""


async def test_identity_maps_only_unambiguous_inns(gateway: ChdbGateway) -> None:
    await Seeder(gateway).suppliers(ALPHA, TWIN, GAMMA)
    identity = ClickHouseSupplierIdentity(gateway)
    found = await identity.ids_by_inn(["7801234564", " 780123456724 ", "0000000000"])
    assert found == {"780123456724": GAMMA.supplier_id}
    assert await identity.ids_by_inn(["", " "]) == {}


async def test_catalog_returns_cards_with_sources_and_match_status(gateway: ChdbGateway) -> None:
    seeder = Seeder(gateway)
    accepted = make_offer("accepted", supplier=ALPHA)
    stale = replace(make_offer("stale", supplier=ALPHA), content_hash="new")
    plain = make_offer("plain", supplier=ALPHA)
    await seeder.sources(make_source())
    await seeder.offers(accepted, stale, plain)
    await seeder.match(accepted.offer_id, "accepted")
    await seeder.match(stale.offer_id, "accepted", content_hash="old")
    catalog = ClickHouseOfferCatalog(gateway)
    cards = await catalog.get_many([accepted.offer_id, stale.offer_id, plain.offer_id])
    assert cards[accepted.offer_id].offer == accepted
    assert cards[accepted.offer_id].source == make_source()
    assert cards[accepted.offer_id].match_status == MatchStatus.ACCEPTED
    assert cards[accepted.offer_id].catalog_confirmed
    assert cards[stale.offer_id].match_status == MatchStatus.ACCEPTED
    assert cards[stale.offer_id].matched_content_hash == "old"
    assert not cards[stale.offer_id].catalog_confirmed
    assert cards[plain.offer_id].match_status == MatchStatus.UNMATCHED
    assert not cards[plain.offer_id].catalog_confirmed
    assert await catalog.get_many([]) == {}


async def test_current_cards_are_latest_available_per_supplier(gateway: ChdbGateway) -> None:
    seeder = Seeder(gateway)
    await seeder.sources(make_source())
    fresh = replace(make_offer("fresh", supplier=ALPHA), last_seen_at=CHECKED + timedelta(days=1))
    older = make_offer("older", supplier=ALPHA)
    gone = make_offer("gone", supplier=ALPHA, availability=Availability.UNAVAILABLE)
    other = make_offer("other", supplier=GAMMA)
    await seeder.offers(fresh, older, gone, other)
    catalog = ClickHouseOfferCatalog(gateway)
    current = await catalog.current_for([ALPHA.supplier_id, GAMMA.supplier_id], 1)
    assert [card.offer.offer_id for card in current[ALPHA.supplier_id]] == [fresh.offer_id]
    assert [card.offer.offer_id for card in current[GAMMA.supplier_id]] == [other.offer_id]
    both = await catalog.current_for([ALPHA.supplier_id], 5)
    assert [card.offer.external_id for card in both[ALPHA.supplier_id]] == ["fresh", "older"]
    assert await catalog.current_for([], 5) == {}
    assert await catalog.current_for([ALPHA.supplier_id], 0) == {}


async def test_probe_answers_when_engine_is_up(gateway: ChdbGateway) -> None:
    probe = ClickHouseProbe(gateway)
    assert probe.name == "clickhouse"
    await probe.check()
