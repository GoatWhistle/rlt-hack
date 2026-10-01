from dataclasses import replace

from src.models.enums import ItemOrigin, LotStatus, WarningCode
from src.models.search_result import SearchWarning
from src.service.procurement_upload.processor import LotProcessor
from src.service.procurement_upload.settings import UploadSettings
from tests.fakes.domain import make_item, make_query
from tests.fakes.ports import FakeInterpreter, FakeRetriever, FixedClock
from tests.fakes.uploads import make_lot
from tests.service.supplier_search.test_service import Harness


async def test_lot_processing_keeps_the_search_warnings_and_pipeline() -> None:
    harness = Harness(history_channel=FakeRetriever("history", fails=True))
    processor = LotProcessor(harness.pipeline(), FixedClock(), UploadSettings())
    result = await processor.process(make_lot())
    searched = await harness.service().search(make_query())
    assert SearchWarning(WarningCode.CHANNEL_FAILED, "history") in result.warnings
    assert result.pipeline is not None
    assert result.pipeline.version == searched.pipeline.version
    assert result.status == LotStatus.NEEDS_CHECK


async def test_mixed_items_warn_about_inference() -> None:
    inferred = replace(make_item("i2", "Рис"), origin=ItemOrigin.INFERRED)
    harness = Harness(interpreter=FakeInterpreter((make_item("i1"), inferred)))
    result = await harness.service().search(make_query())
    assert SearchWarning(WarningCode.ITEMS_INFERRED) in result.warnings
