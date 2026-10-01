import pytest

from src.models.enums import Availability, CompanyRole
from src.service.errors import SupplierNotFoundError
from src.service.supplier_profile.service import SupplierProfileService
from src.service.supplier_search.assembly.role import RoleResolver
from tests.fakes.domain import make_offer, make_offer_evidence, make_supplier
from tests.fakes.ports import FakeDirectory, FakeOfferCatalog

ALPHA = make_supplier("alpha")


def service() -> SupplierProfileService:
    current = make_offer_evidence(make_offer("current", supplier=ALPHA))
    withdrawn = make_offer_evidence(
        make_offer("withdrawn", supplier=ALPHA, availability=Availability.UNAVAILABLE)
    )
    return SupplierProfileService(
        FakeDirectory((ALPHA,)),
        FakeOfferCatalog((current, withdrawn)),
        RoleResolver(),
        offers_per_supplier=50,
    )


async def test_profile_shows_current_cards_and_role() -> None:
    profile = await service().get(ALPHA.supplier_id)
    assert profile.supplier == ALPHA
    assert [card.offer.external_id for card in profile.offers] == ["current"]
    assert profile.role == CompanyRole.DISTRIBUTOR
    assert profile.role_evidence == profile.offers[0].role_evidence


async def test_unknown_supplier_is_not_found() -> None:
    with pytest.raises(SupplierNotFoundError):
        await service().get(make_supplier("ghost").supplier_id)


async def test_supplier_without_cards_has_unknown_role() -> None:
    lonely = SupplierProfileService(FakeDirectory((ALPHA,)), FakeOfferCatalog(), RoleResolver())
    profile = await lonely.get(ALPHA.supplier_id)
    assert (profile.role, profile.offers, profile.role_evidence) == (CompanyRole.UNKNOWN, (), None)
