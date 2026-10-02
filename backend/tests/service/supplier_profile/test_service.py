from datetime import date
from uuid import UUID

import pytest

from src.models.archive_purchase import ArchivePurchase
from src.models.enums import Availability, CompanyRole, PurchaseOutcome
from src.service.errors import PurchaseNotFoundError, SupplierNotFoundError
from src.service.supplier_profile.service import SupplierProfileService
from tests.fakes.domain import make_offer, make_offer_evidence, make_supplier
from tests.fakes.ports import FakeDirectory, FakeOfferCatalog

ALPHA = make_supplier("alpha")
RECORD = ArchivePurchase("7801234564", "L1", "Поставка", date(2024, 1, 1), PurchaseOutcome.WINNER)


class FakePurchases:
    async def get(self, supplier_id: UUID, lot_id: str) -> ArchivePurchase | None:
        return RECORD if (supplier_id, lot_id) == (ALPHA.supplier_id, "L1") else None


def service() -> SupplierProfileService:
    current = make_offer_evidence(make_offer("current", supplier=ALPHA))
    withdrawn = make_offer_evidence(
        make_offer("withdrawn", supplier=ALPHA, availability=Availability.UNAVAILABLE)
    )
    return SupplierProfileService(
        FakeDirectory((ALPHA,)),
        FakeOfferCatalog((current, withdrawn)),
        FakePurchases(),
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
    lonely = SupplierProfileService(FakeDirectory((ALPHA,)), FakeOfferCatalog(), FakePurchases())
    profile = await lonely.get(ALPHA.supplier_id)
    assert (profile.role, profile.offers, profile.role_evidence) == (CompanyRole.UNKNOWN, (), None)


async def test_archive_purchase_is_found_or_reported() -> None:
    assert await service().purchase(ALPHA.supplier_id, "L1") == RECORD
    with pytest.raises(PurchaseNotFoundError):
        await service().purchase(ALPHA.supplier_id, "L2")
