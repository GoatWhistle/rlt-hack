from dataclasses import replace

from src.models.enums import ItemOrigin, LotStatus, WarningCode
from src.models.search import CandidateLimit, SearchQuery, SearchText
from src.models.search_result import SearchWarning
from src.service.procurement_upload.processor import LotProcessor
from src.service.procurement_upload.settings import UploadSettings
from tests.fakes.domain import make_item, make_query
from tests.fakes.ports import FakeInterpreter, FakeRetriever, FixedClock
from tests.fakes.uploads import make_lot
from tests.service.supplier_search.test_service import Harness


async def test_lot_and_manual_search_share_candidates_and_reasons() -> None:
    harness = Harness(history_channel=FakeRetriever("history", fails=True))
    service = harness.service()
    lot = make_lot()
    result = await LotProcessor(service, FixedClock(), UploadSettings()).process(lot)
    assert result.search_id is not None
    archived = harness.archive.stored[result.search_id]
    manual = await service.search(
        SearchQuery(text=SearchText(lot.search_text), limit=CandidateLimit.default())
    )
    assert archived.candidates == manual.candidates
    assert archived.items == manual.items
    assert archived.pipeline.version == manual.pipeline.version
    assert SearchWarning(WarningCode.CHANNEL_FAILED, "history") in archived.warnings
    assert result.status == LotStatus.NEEDS_CHECK


async def test_context_is_kept_but_text_only_ranking_reports_only_text() -> None:
    harness = Harness()
    lot = make_lot()
    result = await LotProcessor(harness.service(), FixedClock(), UploadSettings()).process(lot)
    assert result.search_id is not None
    archived = harness.archive.stored[result.search_id]
    assert archived.query.context.customer_inn == lot.customer_inn
    assert archived.pipeline.inputs == ("text",)


async def test_mixed_items_warn_about_inference() -> None:
    inferred = replace(make_item("i2", "Рис"), origin=ItemOrigin.INFERRED)
    harness = Harness(interpreter=FakeInterpreter((make_item("i1"), inferred)))
    result = await harness.service().search(make_query())
    assert SearchWarning(WarningCode.ITEMS_INFERRED) in result.warnings
