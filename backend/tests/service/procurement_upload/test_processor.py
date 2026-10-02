from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest

from src.models.enums import LotStatus, SearchOrigin, WarningCode
from src.models.search_result import SearchResult, SearchWarning
from src.service.errors import LotNotArchivedError
from src.service.procurement_upload.processor import LotProcessor
from src.service.procurement_upload.settings import UploadSettings
from tests.fakes.domain import make_candidate, make_result
from tests.fakes.ports import FixedClock
from tests.fakes.upload_ports import FakeLotSearch
from tests.fakes.uploads import make_lot

WARNING = SearchWarning(WarningCode.CHANNEL_FAILED, "history")


def report(*warnings: SearchWarning) -> SearchResult:
    return replace(make_result(make_candidate()), warnings=warnings)


def processor(search: FakeLotSearch, settings: UploadSettings | None = None) -> LotProcessor:
    return LotProcessor(search, FixedClock(), settings or UploadSettings())


async def test_lot_runs_the_shared_archived_search_with_its_context() -> None:
    found = report(WARNING)
    search = FakeLotSearch(found)
    result = await processor(search, UploadSettings(candidates_per_lot=7)).process(make_lot())
    query = search.queries[0]
    assert query.text.value == "Крупа гречневая ядрица 500 кг"
    assert query.limit.value == 7
    assert query.origin == SearchOrigin.UPLOAD
    assert (query.context.customer_inn, query.context.start_price) == (
        "7807022750",
        Decimal("2835.54"),
    )
    assert (result.lot_id, result.search_id) == ("4257576", found.search_id)
    assert (result.products, result.candidates) == (1, 1)


async def test_unarchived_search_is_retried_not_saved() -> None:
    search = FakeLotSearch(report(), unarchived=True)
    with pytest.raises(LotNotArchivedError):
        await processor(search).process(make_lot())


async def test_failed_channel_is_kept_and_needs_a_check() -> None:
    clean = await processor(FakeLotSearch(report())).process(make_lot())
    degraded = await processor(FakeLotSearch(report(WARNING))).process(make_lot())
    assert clean.status == LotStatus.READY
    assert degraded.status == LotStatus.NEEDS_CHECK


async def test_lot_without_items_has_no_candidates() -> None:
    result = await processor(FakeLotSearch(None)).process(make_lot())
    assert (result.search_id, result.candidates, result.failed) == (None, 0, False)
    assert result.status == LotStatus.NO_CANDIDATES


async def test_slow_lot_times_out() -> None:
    search = FakeLotSearch(report(), delay=1.0)
    settings = UploadSettings(lot_timeout_seconds=0.05)
    with pytest.raises(TimeoutError):
        await processor(search, settings).process(make_lot())


@pytest.mark.parametrize(
    "changes",
    [
        {"max_rows": 0},
        {"candidates_per_lot": 51},
        {"lot_timeout_seconds": 0},
        {"retry_delay_seconds": -1},
    ],
)
def test_settings_reject_impossible_values(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=r"must|cannot"):
        UploadSettings(**changes)
