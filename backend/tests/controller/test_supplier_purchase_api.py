from datetime import date

import httpx

from src.models.archive_purchase import ArchivePurchase
from src.models.enums import PurchaseOutcome
from tests.fakes.http import FakeServiceProvider

PURCHASE = ArchivePurchase(
    supplier_inn="7801234564",
    lot_id="4012345",
    title="Поставка крупы",
    published=date(2024, 11, 6),
    outcome=PurchaseOutcome.WINNER,
    category="10.61",
    products=("Крупа гречневая",),
    snapshot="idx",
)


async def test_archive_purchase_is_read_by_supplier_and_lot(
    client: httpx.AsyncClient, provider: FakeServiceProvider
) -> None:
    supplier = provider.profiles.profile.supplier.supplier_id
    provider.profiles.purchases = {"4012345": PURCHASE}
    response = await client.get(f"/api/suppliers/{supplier}/purchases/4012345")
    assert response.status_code == 200
    body = response.json()
    assert body["provenance"] == "procurementArchive"
    assert (body["publishedAt"], body["outcome"], body["customerInn"]) == (
        "2024-11-06",
        "winner",
        None,
    )
    missing = await client.get(f"/api/suppliers/{supplier}/purchases/other")
    assert (missing.status_code, missing.json()["code"]) == (404, "purchase_not_found")
    assert missing.json()["message"] == "archive purchase not found"
    bad = await client.get(f"/api/suppliers/{supplier}/purchases/bad%20id")
    assert bad.status_code == 422
