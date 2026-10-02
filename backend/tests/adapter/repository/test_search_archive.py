from dataclasses import replace
from datetime import timedelta

import pytest

from src.adapter.repository.clickhouse.search.search_archive.archive import ClickHouseSearchArchive
from tests.clickhouse.chdb_gateway import ChdbGateway
from tests.fakes.domain import MOMENT, make_candidate, make_result, make_supplier, uid

pytest.importorskip("chdb")
pytestmark = pytest.mark.chdb


async def test_archive_saves_reads_and_lists_searches(gateway: ChdbGateway) -> None:
    archive = ClickHouseSearchArchive(gateway)
    result = make_result(make_candidate(), make_candidate(make_supplier("beta"), rank=2))
    await archive.save(result)
    await archive.save(result)
    assert await archive.get(result.search_id) == result
    assert await archive.get(uid("missing")) is None
    history = await archive.recent(5)
    assert history.searches == (result.summary(),)
    assert (history.has_more, history.total) == (False, 1)
    assert (await archive.recent(0)).searches == ()


async def test_archive_pages_history_after_a_cursor(gateway: ChdbGateway) -> None:
    archive = ClickHouseSearchArchive(gateway)
    base = make_result(make_candidate())
    results = [
        replace(
            base, search_id=uid(f"search-{index}"), created_at=MOMENT + timedelta(minutes=index)
        )
        for index in range(3)
    ]
    for result in results:
        await archive.save(result)
    first = await archive.recent(2)
    assert [item.search_id for item in first.searches] == [uid("search-2"), uid("search-1")]
    assert (first.has_more, first.total) == (True, 3)
    rest = await archive.recent(2, first.searches[-1].search_id)
    assert [item.search_id for item in rest.searches] == [uid("search-0")]
    assert rest.has_more is False
