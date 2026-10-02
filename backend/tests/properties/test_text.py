import asyncio
import math
from datetime import UTC, datetime, timedelta, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.adapter.text.analyzer.analyzer import RussianAnalyzer
from src.adapter.text.rule_interpreter.interpreter import MAX_ITEMS, RuleQueryInterpreter
from src.controller.http.locale import parse_accept_language
from src.controller.http.schema import rfc3339
from src.models.enums import Locale
from src.models.errors import EmptySearchTextError, SearchTextTooLongError
from src.models.scoring import Score
from src.models.search import SearchQuery, SearchText

ALPHABET = st.characters(
    codec="utf-8",
    categories=("L", "N", "P", "Z", "S"),
    include_characters="".join(map(chr, (0x200B, 0xFEFF, 0xBD, 0x663, 0x3B, 0x2C, 0x0A, 0x09))),
)
TEXTS = st.text(ALPHABET, max_size=600)
INTERPRETER = RuleQueryInterpreter(RussianAnalyzer())


@given(TEXTS)
def test_search_text_is_normalized_once(raw: str) -> None:
    collapsed = " ".join(raw.split())
    if not collapsed:
        with pytest.raises(EmptySearchTextError):
            SearchText(raw)
        return
    text = SearchText(raw)
    assert SearchText(text.value) == text
    assert text.value == collapsed


@given(st.integers(SearchText.MAX_LENGTH + 1, SearchText.MAX_LENGTH * 2))
def test_search_text_rejects_long_input(length: int) -> None:
    with pytest.raises(SearchTextTooLongError):
        SearchText("а" * length)


@settings(max_examples=150, deadline=None)
@given(TEXTS.filter(lambda raw: bool(raw.split())))
def test_interpreter_returns_bounded_well_formed_items(raw: str) -> None:
    items = asyncio.run(INTERPRETER.interpret(SearchQuery(SearchText(raw))))
    assert len(items) <= MAX_ITEMS
    assert len({item.item_id for item in items}) == len(items)
    assert all(item.name.strip() for item in items)
    assert all(item.quantity is None or item.quantity.value > 0 for item in items)


@given(st.floats(allow_nan=True, allow_infinity=True))
def test_score_clamp_stays_within_unit_interval(value: float) -> None:
    clamped = Score.clamp(value).value
    assert 0.0 <= clamped <= 1.0
    assert math.isfinite(clamped)


@given(st.text(max_size=200))
def test_accept_language_never_fails(header: str) -> None:
    assert parse_accept_language(header) in tuple(Locale)


@given(
    st.datetimes(
        min_value=datetime(1970, 1, 2),
        max_value=datetime(9999, 12, 30),
        timezones=st.sampled_from((UTC, timezone(timedelta(hours=3)), None)),
    )
)
def test_rfc3339_always_ends_in_utc(moment: datetime) -> None:
    assert rfc3339(moment).endswith("Z")
