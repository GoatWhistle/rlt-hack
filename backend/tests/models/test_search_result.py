from dataclasses import replace

import pytest

from src.models.enums import CheckReason, ComponentState, Locale
from src.models.errors import InvalidSearchResultError
from src.models.health import ComponentHealth, Readiness
from tests.fakes.domain import make_candidate, make_item, make_query, make_result, make_supplier


def test_result_summarises_itself() -> None:
    result = make_result(
        make_candidate(make_supplier("alpha"), rank=1),
        make_candidate(make_supplier("beta"), rank=2, reasons=(CheckReason.INN_MISSING,)),
    )
    summary = result.summary()
    assert (summary.items, summary.candidates, summary.recommended) == (1, 2, 1)
    assert summary.locale == Locale.RU
    assert summary.text == result.query.text


def test_result_ranks_run_in_order() -> None:
    with pytest.raises(InvalidSearchResultError):
        make_result(make_candidate(rank=2))


def test_result_respects_the_limit() -> None:
    result = make_result(make_candidate(make_supplier("a")), replace(make_candidate(), rank=2))
    with pytest.raises(InvalidSearchResultError):
        replace(result, query=make_query(limit=1))


def test_result_matches_point_to_known_items() -> None:
    with pytest.raises(InvalidSearchResultError):
        make_result(make_candidate(item_id="i9"), items=(make_item("i1"),))


def test_readiness_needs_every_component_up() -> None:
    up = ComponentHealth("clickhouse", ComponentState.UP)
    down = ComponentHealth("ml", ComponentState.DOWN)
    assert Readiness((up,)).ready
    assert not Readiness((up, down)).ready
