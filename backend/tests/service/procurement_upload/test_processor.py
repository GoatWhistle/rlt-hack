from typing import Any

import pytest

from src.models.enums import WarningCode
from src.models.search_result import SearchWarning
from src.service.procurement_upload.processor import LotProcessor
from src.service.procurement_upload.settings import UploadSettings
from src.service.supplier_search.matcher import MatchOutcome
from tests.fakes.domain import make_candidate, make_item
from tests.fakes.ports import FakeInterpreter, FixedClock
from tests.fakes.upload_ports import FakeMatcher
from tests.fakes.uploads import make_lot

WARNING = SearchWarning(WarningCode.CHANNEL_FAILED, "history")


def processor(
    interpreter: FakeInterpreter, matcher: FakeMatcher, settings: UploadSettings | None = None
) -> LotProcessor:
    return LotProcessor(interpreter, matcher, FixedClock(), settings or UploadSettings())


async def test_lot_text_becomes_items_and_ranked_candidates() -> None:
    interpreter = FakeInterpreter((make_item(),))
    matcher = FakeMatcher(MatchOutcome((make_candidate(),), ("lexical",), (WARNING,)))
    result = await processor(interpreter, matcher, UploadSettings(candidates_per_lot=7)).process(
        make_lot()
    )
    assert interpreter.calls[0].text.value == "Крупа гречневая ядрица 500 кг"
    assert interpreter.calls[0].limit.value == 7
    assert matcher.requests[0].items == (make_item(),)
    assert (result.lot_id, result.items, result.warnings) == ("4257576", (make_item(),), (WARNING,))
    assert [candidate.rank for candidate in result.candidates] == [1]


async def test_lot_without_items_has_no_candidates() -> None:
    matcher = FakeMatcher(MatchOutcome((), ()))
    result = await processor(FakeInterpreter(()), matcher).process(make_lot())
    assert (result.items, result.candidates, result.failed) == ((), (), False)
    assert matcher.requests == []


async def test_slow_lot_times_out() -> None:
    matcher = FakeMatcher(MatchOutcome((), ()), delay=1.0)
    settings = UploadSettings(lot_timeout_seconds=0.05)
    with pytest.raises(TimeoutError):
        await processor(FakeInterpreter((make_item(),)), matcher, settings).process(make_lot())


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
