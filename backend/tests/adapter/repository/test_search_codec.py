import json
from dataclasses import replace
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.adapter.repository.clickhouse.search_archive.result_dto import (
    decode_result,
    encode_result,
)
from src.models.candidate import Highlight, ProductMatch
from src.models.enums import (
    CheckReason,
    CompanyRole,
    HighlightCode,
    ItemOrigin,
    ItemType,
    Locale,
    MatchBasis,
    PurchaseOutcome,
    WarningCode,
)
from src.models.purchase import PurchaseRecord, PurchaseSummary
from src.models.query_item import Quantity, QueryItem
from src.models.search import CandidateLimit, SearchFilters, SearchQuery, SearchText
from src.models.search_result import SearchResult, SearchWarning
from tests.fakes.domain import make_candidate, make_result, make_supplier


def rich_result() -> SearchResult:
    items = (
        QueryItem(
            "i1",
            "Крупа гречневая",
            okpd2="10.61.32.113",
            item_type=ItemType.GOODS,
            quantity=Quantity(Decimal("1.5"), "т"),
        ),
        QueryItem("i2", "Рис", origin=ItemOrigin.INFERRED),
    )
    unsure = replace(
        make_candidate(make_supplier("beta", inn=None), rank=2, reasons=(CheckReason.INN_MISSING,)),
        role=CompanyRole.UNKNOWN,
        role_evidence=None,
        matches=(ProductMatch("i2", MatchBasis.INFERRED),),
        history=PurchaseSummary(
            4, 1, (PurchaseRecord("L-01", "Поставка риса", PurchaseOutcome.WINNER, ("i2",)),)
        ),
        highlights=(Highlight(HighlightCode.VERIFIED_IDENTITY),),
    )
    base = make_result(make_candidate(), unsure, items=items)
    query = SearchQuery(
        SearchText("крупа гречневая 1,5 т; рис"),
        CandidateLimit(5),
        Locale.EN,
        SearchFilters(regions=("78", "47"), item_type=ItemType.GOODS),
    )
    warnings = (SearchWarning(WarningCode.CHANNEL_FAILED, "semantic"),)
    return replace(base, query=query, warnings=warnings)


def test_codec_round_trip_is_lossless() -> None:
    result = rich_result()
    payload = encode_result(result)
    assert decode_result(payload) == result
    assert decode_result(encode_result(decode_result(payload))) == result
    document = json.loads(payload)
    assert document["payload_version"] == 1
    assert document["items"][0]["quantity"] == {"value": "1.5", "unit": "т"}


def test_codec_rejects_foreign_payloads() -> None:
    with pytest.raises(ValidationError):
        decode_result('{"search_id": "x"}')
