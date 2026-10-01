import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.adapter.repository.clickhouse.search_archive.result_dto import (
    decode_result,
    encode_result,
)
from src.adapter.repository.clickhouse.upload_store.codec import (
    decode_issues,
    decode_lot_result,
    encode_lot_result,
)
from src.adapter.repository.errors import CorruptRecordError
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
from src.models.lot_result import LotResult
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


FIXTURES = Path(__file__).parent / "fixtures"


def test_v1_payload_still_decodes() -> None:
    payload = (FIXTURES / "search_payload_v1.json").read_text(encoding="utf-8")
    assert decode_result(payload) == rich_result()


def test_codec_rejects_foreign_payloads() -> None:
    with pytest.raises(CorruptRecordError):
        decode_result('{"search_id": "x"}')


def test_unknown_payload_version_is_corrupt() -> None:
    document = json.loads(encode_result(rich_result()))
    document["payload_version"] = 99
    with pytest.raises(CorruptRecordError, match="payload version 99"):
        decode_result(json.dumps(document))


def test_payload_breaking_current_rules_is_corrupt() -> None:
    document = json.loads(encode_result(rich_result()))
    document["query"]["limit"] = 60
    with pytest.raises(CorruptRecordError) as caught:
        decode_result(json.dumps(document))
    assert caught.value.reason == "InvalidCandidateLimitError"


def test_lot_payloads_are_checked_the_same_way() -> None:
    result = LotResult("L-1", datetime(2026, 10, 1, tzinfo=UTC))
    document = json.loads(encode_lot_result(result))
    assert decode_lot_result(json.dumps(document)) == result
    document["payload_version"] = 99
    with pytest.raises(CorruptRecordError):
        decode_lot_result(json.dumps(document))
    document["lot_id"] = ""
    document["payload_version"] = 1
    with pytest.raises(CorruptRecordError):
        decode_lot_result(json.dumps(document))
    with pytest.raises(CorruptRecordError):
        decode_issues('[{"row": 0, "code": "badPrice", "value": ""}]')
