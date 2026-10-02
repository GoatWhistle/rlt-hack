from dataclasses import replace

import pytest

from src.models.company.company_role import RoleAssessment, assess_role, company_role
from src.models.company.offer_evidence import OfferEvidence
from src.models.company.purchase import PurchaseSummary
from src.models.enums import (
    Availability,
    CompanyRole,
    HighlightCode,
    MatchBasis,
    MatchStatus,
    SupplierRole,
    VerificationStatus,
)
from src.service.supplier_search.assembly.highlights import HighlightComposer
from src.service.supplier_search.assembly.match import MatchResolver
from tests.fakes.domain import make_offer, make_offer_evidence, make_supplier
from tests.fakes.drafts import stock_match


def card(
    name: str,
    role: SupplierRole = SupplierRole.DISTRIBUTOR,
    availability: Availability = Availability.AVAILABLE,
    seller: VerificationStatus = VerificationStatus.VERIFIED,
    match: MatchStatus = MatchStatus.UNMATCHED,
    url: str | None = None,
) -> OfferEvidence:
    offer = make_offer(name, role=role, availability=availability, seller_status=seller)
    if url is not None:
        offer = replace(offer, url=url)
    return make_offer_evidence(offer, match_status=match)


@pytest.mark.parametrize(
    ("roles", "expected"),
    [
        ({SupplierRole.MANUFACTURER, SupplierRole.RESELLER}, CompanyRole.MANUFACTURER),
        ({SupplierRole.DISTRIBUTOR, SupplierRole.RESELLER}, CompanyRole.SUPPLIER_DISTRIBUTOR),
        ({SupplierRole.DISTRIBUTOR, SupplierRole.SERVICE_PROVIDER}, CompanyRole.DISTRIBUTOR),
        ({SupplierRole.RESELLER}, CompanyRole.SUPPLIER),
        ({SupplierRole.SERVICE_PROVIDER}, CompanyRole.SERVICE_PROVIDER),
        (set(), CompanyRole.UNKNOWN),
    ],
)
def test_company_role_follows_the_strongest_card(
    roles: set[SupplierRole], expected: CompanyRole
) -> None:
    assert company_role(roles) == expected


def test_role_comes_from_cards_with_a_confirmed_seller() -> None:
    reseller = card("reseller", SupplierRole.RESELLER, seller=VerificationStatus.UNVERIFIED)
    distributor = card("distributor")
    withdrawn = card("old", SupplierRole.MANUFACTURER, Availability.UNAVAILABLE)
    assessed = assess_role((reseller, distributor, withdrawn))
    assert assessed == RoleAssessment(CompanyRole.DISTRIBUTOR, distributor.role_evidence)
    assert assessed.confirmed


def test_role_of_unconfirmed_sellers_has_no_evidence() -> None:
    unverified = card("unverified", seller=VerificationStatus.UNVERIFIED)
    conflicted = card("conflicted", SupplierRole.MANUFACTURER, seller=VerificationStatus.CONFLICT)
    assessed = assess_role((unverified, conflicted))
    assert assessed == RoleAssessment(CompanyRole.MANUFACTURER)
    assert not assessed.confirmed


def test_role_without_any_evidence_or_cards_stays_unconfirmed() -> None:
    blank = card("blank", url="not a link")
    assert assess_role((blank,)) == RoleAssessment(CompanyRole.DISTRIBUTOR)
    assert assess_role(()) == RoleAssessment(CompanyRole.UNKNOWN)
    unknown = card("unknown", SupplierRole.UNKNOWN)
    assert assess_role((unknown,)) == RoleAssessment(CompanyRole.UNKNOWN)


def test_stock_needs_a_current_confirmed_available_card() -> None:
    resolver = MatchResolver()
    stocked = card("stocked")
    match = resolver.resolve(
        "i1", (card("review", seller=VerificationStatus.UNVERIFIED), stocked), True
    )
    assert match is not None
    assert (match.basis, match.offer_id) == (MatchBasis.STOCK, stocked.offer.offer_id)
    assert match.evidence == stocked.evidence


def test_catalog_needs_an_accepted_match_and_a_source() -> None:
    accepted = card("accepted", availability=Availability.UNKNOWN, match=MatchStatus.ACCEPTED)
    match = MatchResolver().resolve("i1", (accepted,), True)
    assert match is not None
    assert match.basis == MatchBasis.CATALOG


def test_catalog_needs_a_confirmed_seller_and_the_matched_content() -> None:
    resolver = MatchResolver()
    unverified = card(
        "unverified",
        availability=Availability.UNKNOWN,
        seller=VerificationStatus.UNVERIFIED,
        match=MatchStatus.ACCEPTED,
    )
    weak = resolver.resolve("i1", (unverified,), True)
    assert weak is not None
    assert weak.basis == MatchBasis.INFERRED
    accepted = card("changed", availability=Availability.UNKNOWN, match=MatchStatus.ACCEPTED)
    stale = replace(accepted, matched_content_hash="before")
    changed = resolver.resolve("i1", (stale,), True)
    assert changed is not None
    assert changed.basis == MatchBasis.INFERRED


def test_unconfirmed_card_or_history_gives_only_an_inferred_match() -> None:
    resolver = MatchResolver()
    unconfirmed = card("unconfirmed", seller=VerificationStatus.UNVERIFIED)
    inferred = resolver.resolve("i1", (unconfirmed,), True)
    assert inferred is not None
    assert (inferred.basis, inferred.offer_id) == (MatchBasis.INFERRED, unconfirmed.offer.offer_id)
    sourceless = card("sourceless", seller=VerificationStatus.UNVERIFIED, url="ftp://x")
    bare = resolver.resolve("i1", (sourceless,), False)
    assert bare is not None
    assert (bare.basis, bare.offer_id, bare.evidence) == (MatchBasis.INFERRED, None, None)
    signal = resolver.resolve("i1", (), True)
    assert signal is not None
    assert signal.evidence is None
    assert resolver.resolve("i1", (), False) is None


def test_highlights_report_counts_as_parameters() -> None:
    supplier = make_supplier()
    stocked = card("stocked")
    matches = (stock_match("i1", stocked),)
    history = PurchaseSummary(similar=4, wins=2)
    highlights = HighlightComposer().compose(supplier, matches, (stocked,), history, 2)
    assert [(item.code, dict(item.params)) for item in highlights] == [
        (HighlightCode.COVERS_ITEMS, {"matched": 1, "total": 2}),
        (HighlightCode.IN_STOCK, {"count": 1}),
        (HighlightCode.HAS_PRICE, {"count": 1}),
        (HighlightCode.PAST_WINS, {"count": 2}),
        (HighlightCode.SIMILAR_PURCHASES, {"count": 4}),
        (HighlightCode.VERIFIED_IDENTITY, {}),
    ]


def test_highlights_skip_empty_counters_and_unverified_identity() -> None:
    supplier = replace(make_supplier(), identity_status=VerificationStatus.UNVERIFIED)
    assert HighlightComposer().compose(supplier, (), (), PurchaseSummary(), 1) == ()
    no_inn = make_supplier(inn=None)
    assert HighlightComposer().compose(no_inn, (), (), PurchaseSummary(), 1) == ()
