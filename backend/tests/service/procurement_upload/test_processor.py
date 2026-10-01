from typing import Any

import pytest

from src.models.enums import LotStatus, WarningCode
from src.models.match import MatchReport
from src.models.search_result import PipelineInfo, SearchWarning
from src.service.procurement_upload.processor import LotProcessor
from src.service.procurement_upload.settings import UploadSettings
from tests.fakes.domain import MOMENT, make_candidate, make_item
from tests.fakes.ports import FixedClock
from tests.fakes.upload_ports import FakeLotSearch
from tests.fakes.uploads import make_lot

WARNING = SearchWarning(WarningCode.CHANNEL_FAILED, "history")
PIPELINE = PipelineInfo(version="search-v1", channels=("lexical",), as_of=MOMENT)


def report(*warnings: SearchWarning) -> MatchReport:
    return MatchReport((make_item(),), (make_candidate(),), PIPELINE, warnings)


def processor(search: FakeLotSearch, settings: UploadSettings | None = None) -> LotProcessor:
    return LotProcessor(search, FixedClock(), settings or UploadSettings())


async def test_lot_text_runs_the_search_pipeline() -> None:
    search = FakeLotSearch(report(WARNING))
    result = await processor(search, UploadSettings(candidates_per_lot=7)).process(make_lot())
    assert search.queries[0].text.value == "Крупа гречневая ядрица 500 кг"
    assert search.queries[0].limit.value == 7
    assert (result.lot_id, result.items, result.warnings) == ("4257576", (make_item(),), (WARNING,))
    assert result.pipeline == PIPELINE
    assert [candidate.rank for candidate in result.candidates] == [1]


async def test_failed_channel_is_kept_and_needs_a_check() -> None:
    clean = await processor(FakeLotSearch(report())).process(make_lot())
    degraded = await processor(FakeLotSearch(report(WARNING))).process(make_lot())
    assert clean.status == LotStatus.READY
    assert degraded.status == LotStatus.NEEDS_CHECK


async def test_lot_without_items_has_no_candidates() -> None:
    result = await processor(FakeLotSearch(None)).process(make_lot())
    assert (result.items, result.candidates, result.failed) == ((), (), False)
    assert result.pipeline is None


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
