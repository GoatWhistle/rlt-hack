import pytest

from src.adapter.repository.clickhouse.search.search_archive.archive import ClickHouseSearchArchive
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.fakes.domain import make_candidate, make_result, make_supplier, uid

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb


async def test_archive_saves_reads_and_lists_searches(gateway: ChdbGateway) -> None:
    archive = ClickHouseSearchArchive(gateway)
    result = make_result(make_candidate(), make_candidate(make_supplier("beta"), rank=2))
    await archive.save(result)
    await archive.save(result)
    assert await archive.get(result.search_id) == result
    assert await archive.get(uid("missing")) is None
    assert await archive.recent(5) == (result.summary(),)
    assert await archive.recent(0) == ()
