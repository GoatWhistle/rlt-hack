from dataclasses import replace

from src.models.enums import ItemOrigin, WarningCode
from src.models.search.search_result import SearchWarning
from tests.fakes.domain import make_item, make_query
from tests.fakes.ports import FakeInterpreter
from tests.service.supplier_search.test_service import Harness


async def test_mixed_items_warn_about_inference() -> None:
    inferred = replace(make_item("i2", "Рис"), origin=ItemOrigin.INFERRED)
    harness = Harness(interpreter=FakeInterpreter((make_item("i1"), inferred)))
    result = await harness.service().search(make_query())
    assert SearchWarning(WarningCode.ITEMS_INFERRED) in result.warnings
