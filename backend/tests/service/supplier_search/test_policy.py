from dataclasses import replace

import pytest

from src.models.candidate import ProductMatch
from src.models.enums import (
    Availability,
    CandidateStatus,
    CheckReason,
    CompanyRole,
    MatchBasis,
    VerificationStatus,
)
from src.service.supplier_search.policy.coverage import CoverageRule
from src.service.supplier_search.policy.current_offer import CurrentOfferRule
from src.service.supplier_search.policy.identity_conflict import IdentityConflictRule
from src.service.supplier_search.policy.inn_required import InnRequiredRule
from src.service.supplier_search.policy.policy import CandidatePolicy
from src.service.supplier_search.policy.role_confirmed import RoleConfirmedRule
from src.service.supplier_search.policy.source_availability import SourceAvailabilityRule
from tests.fakes.domain import make_offer, make_offer_evidence, make_source, make_supplier
from tests.fakes.drafts import make_draft, stock_match


@pytest.mark.parametrize("inn", [None, "", "12345", "78012345678", "78012345ab", "7801234567890"])
def test_inn_rule_flags_missing_or_malformed_inn(inn: str | None) -> None:
    outcome = InnRequiredRule().apply(make_draft(make_supplier(inn=inn)))
    assert (outcome.reason, outcome.triggered) == (CheckReason.INN_MISSING, True)


@pytest.mark.parametrize("inn", ["7801234567", "780123456789"])
def test_inn_rule_accepts_ten_or_twelve_digits(inn: str) -> None:
    assert not InnRequiredRule().apply(make_draft(make_supplier(inn=inn))).triggered


def test_identity_rule_flags_company_and_card_conflicts() -> None:
    rule = IdentityConflictRule()
    conflicted = replace(make_supplier(), identity_status=VerificationStatus.CONFLICT)
    assert rule.apply(make_draft(conflicted)).triggered
    seller = make_offer_evidence(make_offer(seller_status=VerificationStatus.CONFLICT))
    assert rule.apply(make_draft(cards=(seller,))).triggered
    source = replace(make_source(), ownership_status=VerificationStatus.CONFLICT)
    owned = make_offer_evidence(source=source)
    assert rule.apply(make_draft(cards=(owned,))).triggered
    clean = rule.apply(make_draft())
    assert (clean.reason, clean.triggered) == (CheckReason.IDENTITY_CONFLICT, False)


def test_role_rule_needs_a_known_role_with_a_source() -> None:
    rule = RoleConfirmedRule()
    assert rule.apply(make_draft(role=CompanyRole.UNKNOWN)).triggered
    assert rule.apply(replace(make_draft(), role_evidence=None)).triggered
    outcome = rule.apply(make_draft())
    assert (outcome.reason, outcome.triggered) == (CheckReason.ROLE_UNCONFIRMED, False)


def test_current_offer_rule_needs_a_current_card_with_a_confirmed_seller() -> None:
    rule = CurrentOfferRule()
    assert rule.apply(make_draft(cards=())).triggered
    withdrawn = make_offer_evidence(make_offer(availability=Availability.UNAVAILABLE))
    assert rule.apply(make_draft(cards=(withdrawn,))).triggered
    unconfirmed = make_offer_evidence(make_offer(seller_status=VerificationStatus.UNVERIFIED))
    assert rule.apply(make_draft(cards=(unconfirmed,))).triggered
    outcome = rule.apply(make_draft())
    assert (outcome.reason, outcome.triggered) == (CheckReason.NO_CURRENT_OFFER, False)


def test_coverage_rule_flags_inferred_only_or_narrow_matches() -> None:
    rule = CoverageRule(0.5)
    inferred = (ProductMatch("i1", MatchBasis.INFERRED),)
    assert rule.apply(make_draft(matches=inferred)).triggered
    assert rule.apply(make_draft(matches=())).triggered
    assert rule.apply(make_draft(total_items=3)).triggered
    covered = make_draft(matches=(stock_match("i1"), ProductMatch("i2", MatchBasis.INFERRED)))
    assert not rule.apply(replace(covered, total_items=2)).triggered
    outcome = rule.apply(make_draft(total_items=2))
    assert (outcome.reason, outcome.triggered) == (CheckReason.RANGE_UNCONFIRMED, False)


@pytest.mark.parametrize("threshold", [0.0, 1.5])
def test_coverage_threshold_must_be_a_share(threshold: float) -> None:
    with pytest.raises(ValueError, match="threshold"):
        CoverageRule(threshold)


def test_source_rule_flags_failed_enrichment() -> None:
    outcome = SourceAvailabilityRule().apply(make_draft(failed=True))
    assert (outcome.reason, outcome.triggered) == (CheckReason.SOURCE_UNAVAILABLE, True)
    assert not SourceAvailabilityRule().apply(make_draft()).triggered


def test_policy_recommends_only_when_no_rule_fires() -> None:
    policy = CandidatePolicy.standard(0.5)
    verdict = policy.evaluate(make_draft())
    assert (verdict.status, verdict.reasons) == (CandidateStatus.RECOMMENDED, ())


def test_policy_lists_reasons_in_rule_order() -> None:
    draft = make_draft(
        make_supplier(inn=None),
        matches=(),
        cards=(),
        role=CompanyRole.UNKNOWN,
        failed=True,
    )
    verdict = CandidatePolicy.standard(0.5).evaluate(draft)
    assert verdict.status == CandidateStatus.CHECK
    assert verdict.reasons == (
        CheckReason.INN_MISSING,
        CheckReason.ROLE_UNCONFIRMED,
        CheckReason.NO_CURRENT_OFFER,
        CheckReason.RANGE_UNCONFIRMED,
        CheckReason.SOURCE_UNAVAILABLE,
    )
