import json
from pathlib import Path

from src.controller.http.errors import HTTP_CODES, INTERNAL, INVALID_REQUEST, KNOWN_ERRORS
from src.models.enums import EnrichmentSource, RetrievalChannel, WarningCode

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
PROXY_CODES = {"rate_limited": 429}


def contract_codes() -> dict[str, int]:
    document = json.loads((CONTRACTS / "error-codes.json").read_text(encoding="utf-8"))
    return {entry["code"]: entry["status"] for entry in document["codes"]}


def backend_codes() -> dict[str, int]:
    kinds = [kind for _, kind in KNOWN_ERRORS]
    found = {kind.code: int(kind.status) for kind in (*kinds, INTERNAL, INVALID_REQUEST)}
    found.update((code, int(status)) for status, code in HTTP_CODES.items())
    return found


def test_every_error_code_is_in_the_contract_with_its_status() -> None:
    assert contract_codes() == {**backend_codes(), **PROXY_CODES}


def test_warning_codes_in_examples_are_known() -> None:
    known = {code.value for code in WarningCode}
    for name in ("search/response.example.json",):
        document = json.loads((CONTRACTS / name).read_text(encoding="utf-8"))
        holder = document if "warnings" in document else document["recommendation"]
        assert {warning["code"] for warning in holder["warnings"]} <= known


def test_channels_and_warning_subjects_come_from_enumerations() -> None:
    subjects = {
        WarningCode.CHANNEL_FAILED: {channel.value for channel in RetrievalChannel},
        WarningCode.ENRICHMENT_FAILED: {source.value for source in EnrichmentSource},
    }
    search = json.loads((CONTRACTS / "search/response.example.json").read_text(encoding="utf-8"))
    channels = set(search["pipeline"]["channels"])
    assert channels <= {channel.value for channel in RetrievalChannel}
    for warning in search["warnings"]:
        allowed = subjects.get(WarningCode(warning["code"]))
        assert allowed is None or warning["subject"] in allowed
