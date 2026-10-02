from datetime import datetime
from decimal import Decimal

import pytest

from src.models.company.evidence import Evidence, is_web_url
from src.models.enums import EvidenceKind, ItemType
from src.models.errors import (
    EmptySearchTextError,
    InvalidCandidateLimitError,
    InvalidEvidenceError,
    InvalidQuantityError,
    InvalidQueryItemError,
    InvalidSearchRequestError,
    SearchTextTooLongError,
)
from src.models.search.query_item import Quantity, QueryItem, SearchRequest
from src.models.search.search import CandidateLimit, SearchFilters, SearchText
from tests.fakes.domain import CHECKED, make_item, make_query


def test_search_text_collapses_whitespace() -> None:
    assert SearchText("  крупа \n\t гречневая  ").value == "крупа гречневая"


def test_search_text_rejects_blank_and_long_values() -> None:
    with pytest.raises(EmptySearchTextError):
        SearchText(" \n ")
    with pytest.raises(SearchTextTooLongError) as error:
        SearchText("а" * (SearchText.MAX_LENGTH + 1))
    assert error.value.limit == SearchText.MAX_LENGTH
    assert len(SearchText("а" * SearchText.MAX_LENGTH).value) == SearchText.MAX_LENGTH


@pytest.mark.parametrize("value", [0, 51, -1])
def test_candidate_limit_has_bounds(value: int) -> None:
    with pytest.raises(InvalidCandidateLimitError):
        CandidateLimit(value)


def test_candidate_limit_defaults_to_twenty() -> None:
    assert CandidateLimit.default().value == 20
    assert make_query().limit.value == 20


def test_filters_drop_blank_and_repeated_regions() -> None:
    filters = SearchFilters(regions=(" 78 ", "", "78", "47"))
    assert filters.regions == ("78", "47")
    assert not filters.is_empty
    assert SearchFilters().is_empty
    assert not SearchFilters(item_type=ItemType.GOODS).is_empty


def test_quantity_needs_positive_value_and_unit() -> None:
    assert Quantity(Decimal(5), " кг ").unit == "кг"
    for value, unit in ((Decimal(0), "кг"), (Decimal(1), " "), (Decimal("NaN"), "кг")):
        with pytest.raises(InvalidQuantityError):
            Quantity(value, unit)


def test_query_item_validates_identity_name_and_code() -> None:
    assert QueryItem("i1", "  Рис \n шлифованный ").name == "Рис шлифованный"
    assert QueryItem("i1", "Рис", okpd2="10.61.11.000").okpd2 == "10.61.11.000"
    with pytest.raises(InvalidQueryItemError):
        QueryItem(" ", "Рис")
    with pytest.raises(InvalidQueryItemError):
        QueryItem("i1", " ")
    with pytest.raises(InvalidQueryItemError):
        QueryItem("i1", "Рис", okpd2="10-61")


def test_search_request_needs_unique_items() -> None:
    request = SearchRequest(make_query(), (make_item("i1"), make_item("i2")))
    assert request.item_ids == ("i1", "i2")
    with pytest.raises(InvalidSearchRequestError):
        SearchRequest(make_query(), ())
    with pytest.raises(InvalidSearchRequestError):
        SearchRequest(make_query(), (make_item("i1"), make_item("i1")))


@pytest.mark.parametrize(
    ("url", "valid"),
    [
        ("https://a.example.org/x", True),
        ("http://a.example.org", True),
        ("ftp://a.example.org", False),
        ("/relative/path", False),
        ("file:///etc/passwd", False),
        ("", False),
    ],
)
def test_evidence_accepts_only_web_addresses(url: str, valid: bool) -> None:
    assert is_web_url(url) is valid


def test_evidence_needs_web_url_and_aware_time() -> None:
    evidence = Evidence(EvidenceKind.PRICE, "  Прайс \n лист ", " https://a.example.org ", CHECKED)
    assert (evidence.title, evidence.url) == ("Прайс лист", "https://a.example.org")
    with pytest.raises(InvalidEvidenceError):
        Evidence(EvidenceKind.PRICE, "x", "javascript:alert(1)", CHECKED)
    with pytest.raises(InvalidEvidenceError):
        Evidence(EvidenceKind.PRICE, "x", "https://a.example.org", datetime(2026, 1, 1))
