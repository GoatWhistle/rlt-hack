import pytest

from src.adapter.repository.clickhouse.archive_roster.store import ClickHouseArchiveRoster
from src.models.archive_roster import RosterSnapshot
from tests.clickhouse.chdb_gateway import ChdbGateway

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb


async def test_roster_is_published_after_its_rows_and_read_by_inn(gateway: ChdbGateway) -> None:
    store = ClickHouseArchiveRoster(gateway)
    assert await store.roster(["7801234564"]) is None
    await store.save(RosterSnapshot.of("inn-a", ["7801234564", "7707083893"]), "a.csv")
    assert await store.saved("inn-a") == 2
    roster = await store.roster(["7801234564", "7736050003", ""])
    assert roster is not None
    assert (roster.version, roster.known) == ("inn-a", frozenset({"7801234564"}))
    assert (await store.roster([])) is not None
