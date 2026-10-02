from dataclasses import replace
from decimal import Decimal

import pytest

from src.models.enums import Availability, VerificationStatus
from src.models.errors import InvalidSearchResultError
from src.models.offer_summary import OfferAttribute, OfferSummary, notable_attributes
from tests.fakes.domain import (
    make_candidate,
    make_offer,
    make_offer_evidence,
    make_result,
)


def test_summary_keeps_offer_facts_and_its_source() -> None:
    offer = replace(
        make_offer("grechka"),
        brand="Увелка",
        article="4607",
        okpd2_code="10.61.32.110",
        seller_status=VerificationStatus.UNVERIFIED,
        attributes={"Фасовка": "50 кг"},
    )
    card = make_offer_evidence(offer)
    summary = OfferSummary.of(card)
    assert (summary.offer_id, summary.name) == (offer.offer_id, "Товар grechka")
    assert (summary.price, summary.currency, summary.unit) == (Decimal("84.50"), "RUB", "кг")
    assert summary.availability == Availability.AVAILABLE
    assert (summary.brand, summary.article, summary.okpd2_code) == (
        "Увелка",
        "4607",
        "10.61.32.110",
    )
    assert summary.seller_status == VerificationStatus.UNVERIFIED
    assert summary.attributes == (OfferAttribute("Фасовка", "50 кг"),)
    assert summary.evidence == card.evidence


def test_offer_without_web_page_has_no_source() -> None:
    card = make_offer_evidence(replace(make_offer(), url="not a url", price=None))
    summary = OfferSummary.of(card)
    assert summary.evidence is None
    assert summary.price is None


def test_only_named_attributes_are_shown_and_at_most_three() -> None:
    raw = {
        "sku_id": "4607",
        "price_kind": "listing",
        "Фасовка": " 50   кг ",
        "Сорт": "первый",
        "Пустое": "  ",
        "Страна": "Россия",
        "Цвет": "светлый",
    }
    assert notable_attributes(raw) == (
        OfferAttribute("Фасовка", "50 кг"),
        OfferAttribute("Сорт", "первый"),
        OfferAttribute("Страна", "Россия"),
    )
    assert notable_attributes({}) == ()


def test_result_rejects_a_repeated_offer() -> None:
    summary = OfferSummary.of(make_offer_evidence())
    result = make_result(make_candidate())
    assert replace(result, offers=(summary,)).offers == (summary,)
    with pytest.raises(InvalidSearchResultError, match="offer is listed twice"):
        replace(result, offers=(summary, summary))
