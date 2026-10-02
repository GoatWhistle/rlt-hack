from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field

from src.models.enums import SearchStage, WarningCode
from src.models.search.search_result import SearchResult, SearchWarning
from src.service.supplier_search.settings import SearchSettings
from tests.fakes.domain import make_item, make_query
from tests.fakes.ports import FakeArchive, FakeInterpreter
from tests.service.supplier_search.test_service import Harness


@dataclass(slots=True)
class RecordedStages:
    names: list[str] = field(default_factory=list)

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        yield
        self.names.append(name)


@dataclass(slots=True)
class CountedShare:
    entered: int = 0
    active: bool = False

    @asynccontextmanager
    async def scope(self) -> AsyncIterator[None]:
        self.entered += 1
        self.active = True
        try:
            yield
        finally:
            self.active = False


@dataclass(slots=True)
class ShareAwareArchive(FakeArchive):
    share: CountedShare = field(default_factory=CountedShare)
    saved_inside_share: list[bool] = field(default_factory=list)

    async def save(self, result: SearchResult) -> None:
        self.saved_inside_share.append(self.share.active)
        await FakeArchive.save(self, result)


async def test_items_beyond_limit_are_dropped_with_warning() -> None:
    items = tuple(make_item(f"i{index}", f"Позиция {index}") for index in range(5))
    harness = Harness(interpreter=FakeInterpreter(items), settings=SearchSettings(max_items=3))
    result = await harness.service().search(make_query())
    assert [item.item_id for item in result.items] == ["i0", "i1", "i2"]
    assert SearchWarning(WarningCode.ITEMS_TRUNCATED) in result.warnings
    assert [len(request.items) for request, _ in harness.lexical.calls] == [3]


async def test_items_within_limit_have_no_truncation_warning() -> None:
    result = await Harness().service().search(make_query())
    assert SearchWarning(WarningCode.ITEMS_TRUNCATED) not in result.warnings


async def test_every_stage_is_timed_once() -> None:
    stages = RecordedStages()
    await Harness(stages=stages).service().search(make_query())
    assert stages.names == [
        SearchStage.PARSE,
        SearchStage.CHANNELS,
        SearchStage.ENRICH,
        SearchStage.POLICY,
        SearchStage.ARCHIVE,
    ]


async def test_search_runs_in_share_scope_and_archive_outside_it() -> None:
    share = CountedShare()
    archive = ShareAwareArchive(share=share)
    result = await Harness(share=share, archive=archive).service().search(make_query())
    assert share.entered == 1
    assert archive.saved_inside_share == [False]
    assert result.search_id in archive.stored


async def test_archive_has_its_own_budget_after_search() -> None:
    harness = Harness(
        archive=FakeArchive(delay=0.1),
        settings=SearchSettings(timeout_seconds=0.05, archive_timeout_seconds=0.5),
    )
    result = await harness.service().search(make_query())
    assert result.warnings == ()
    assert harness.archive.stored == {result.search_id: result}
