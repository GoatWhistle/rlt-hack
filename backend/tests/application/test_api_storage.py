from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from src.adapter.repository.clickhouse.search_archive.archive import ClickHouseSearchArchive
from src.application.config import AppConfig
from src.application.container import Container
from src.application.deferred_gateway import DeferredShare
from tests.application.test_api import RecordingGateway
from tests.fakes.domain import make_candidate, make_result


@dataclass(slots=True)
class FlagShare:
    resolved: int = 0
    active: bool = False

    @asynccontextmanager
    async def scope(self) -> AsyncIterator[None]:
        self.active = True
        try:
            yield
        finally:
            self.active = False


async def test_deferred_share_resolves_on_first_scope() -> None:
    share = FlagShare()

    async def resolve() -> FlagShare:
        share.resolved += 1
        return share

    deferred = DeferredShare(resolve)
    assert share.resolved == 0
    seen: list[bool] = []
    async with deferred.scope():
        seen.append(share.active)
    seen.append(share.active)
    assert seen == [True, False]
    assert share.resolved == 1


async def test_archive_writes_through_writer_and_reads_through_pool() -> None:
    reader = RecordingGateway(rows=[])
    writer = RecordingGateway()
    archive = ClickHouseSearchArchive(reader, writer=writer)
    result = make_result(make_candidate())
    await archive.save(result)
    assert await archive.get(result.search_id) is None
    assert writer.statements == ["supplier_search.searches"]
    assert reader.statements
    assert "supplier_search.searches" not in reader.statements


async def test_container_keeps_a_single_writer_and_halves_search_share() -> None:
    container = Container(AppConfig())
    writer = await container.writer_gateway()
    assert writer is await container.writer_gateway()
    assert writer.size == 1
    interactive = await container.api_gateway()
    assert interactive.share == 2
    await container.aclose()
    assert await container.writer_gateway() is not writer
    await container.aclose()
