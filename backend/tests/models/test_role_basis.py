from dataclasses import replace

from src.models.company_role import assess_role, registry_role
from src.models.enums import CompanyRole, RoleBasis, SupplierRole
from tests.fakes.domain import make_offer, make_offer_evidence, make_supplier

DECLARED = "Заявляет собственную продукцию, ОКПД2 10.61 (реестр МСП ФНС на 10.09.2026)"
OKVED = "Основной ОКВЭД 46.38 «Торговля оптом» (реестр МСП ФНС на 10.09.2026)"


def test_offer_role_names_the_product_it_rests_on() -> None:
    supplier = make_supplier("alpha")
    card = make_offer_evidence(make_offer("buckwheat", supplier=supplier))
    role = assess_role((card,), supplier)
    assert (role.role, role.basis, role.product) == (
        CompanyRole.DISTRIBUTOR,
        RoleBasis.OFFER,
        card.offer.name,
    )
    assert role.confirmed
    assert not role.conflict


def test_registry_declaration_confirms_and_okved_rule_only_suggests() -> None:
    declared = replace(
        make_supplier("alpha"), role=SupplierRole.MANUFACTURER, role_evidence=DECLARED
    )
    confirmed = registry_role(declared)
    assert (confirmed.role, confirmed.basis, confirmed.confirmed) == (
        CompanyRole.MANUFACTURER,
        RoleBasis.REGISTRY,
        True,
    )
    assert confirmed.evidence is not None
    assert confirmed.evidence.url.endswith(declared.inn or "")
    assert confirmed.evidence.checked_at.date().isoformat() == "2026-09-10"
    okved = replace(make_supplier("beta"), role=SupplierRole.DISTRIBUTOR, role_evidence=OKVED)
    suggested = assess_role((), okved)
    assert (suggested.role, suggested.basis, suggested.confirmed) == (
        CompanyRole.DISTRIBUTOR,
        RoleBasis.OKVED,
        False,
    )
    assert suggested.note == OKVED
    assert assess_role((), make_supplier("gamma")).basis == RoleBasis.NONE


def test_disagreeing_sources_are_reported_as_a_conflict() -> None:
    supplier = replace(
        make_supplier("alpha"), role=SupplierRole.MANUFACTURER, role_evidence=DECLARED
    )
    card = make_offer_evidence(make_offer("buckwheat", supplier=supplier))
    role = assess_role((card,), supplier)
    assert (role.role, role.basis, role.conflict, role.note) == (
        CompanyRole.DISTRIBUTOR,
        RoleBasis.OFFER,
        True,
        DECLARED,
    )
