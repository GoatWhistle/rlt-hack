"""Проверка адаптера Пульс цен на подготовленных документах без сети."""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.supplier.errors import BotProtectionError, SourceUnavailableError
from src.adapter.supplier.pulscen_web import PulscenWebProvider
from src.models.enums import Availability, SourceType, SupplierRole
from tests.supplier.fixtures import (
    PULSCEN_BOT_CHECK,
    PULSCEN_FIRMS_PAGE,
    PULSCEN_FIRMS_PAGE_2,
    PULSCEN_PRICE_PAGE,
    PULSCEN_SITEMAP,
    SITEMAP_GOODS,
)
from tests.supplier.provider_smoke import source, transport

BASE = "https://www.pulscen.ru"

PAGES = {
    f"{BASE}/sitemap.xml": PULSCEN_SITEMAP,
    f"{BASE}/firms/010301-armatura": PULSCEN_FIRMS_PAGE,
    f"{BASE}/firms/010301-armatura?page=2": PULSCEN_FIRMS_PAGE_2,
    f"{BASE}/price/010301-armatura": PULSCEN_PRICE_PAGE,
}


def provider(pages: dict[str, str], failing: tuple[str, ...] = ()) -> PulscenWebProvider:
    directory = source("Пульс цен", f"{BASE}/", SourceType.DIRECTORY, "pulscen_web")
    return PulscenWebProvider(directory, delay_seconds=0, transport=transport(pages, failing))


async def expect(error: type[Exception], pages: dict[str, str], failing: tuple[str, ...] = ()):
    try:
        await provider(pages, failing).fetch()
    except error:
        return
    raise AssertionError(f"ожидалась ошибка {error.__name__}")


async def main() -> None:
    package = await provider(PAGES).fetch()
    names = sorted(supplier.name for supplier in package.suppliers)
    assert names == ["АМК-Групп", "ПервоСтрой, ООО"], names
    first = next(s for s in package.suppliers if s.name == "ПервоСтрой, ООО")
    assert first.website == "https://pervostroi.example"
    assert first.region == "г. Новосибирск, ул. Ватутина, 99"
    assert first.inn is None
    assert len(package.offers) == 2
    priced = next(o for o in package.offers if o.external_id == "185531520")
    assert priced.price == Decimal("68.55") and priced.currency == "RUB"
    assert priced.availability == Availability.AVAILABLE
    assert priced.supplier_role == SupplierRole.UNKNOWN and priced.supplier_id is None
    unpriced = next(o for o in package.offers if o.external_id == "185531999")
    assert unpriced.price is None and unpriced.availability == Availability.UNKNOWN

    repeated = await provider(PAGES).fetch()
    assert sorted(o.offer_id for o in repeated.offers) == sorted(o.offer_id for o in package.offers)
    assert sorted(s.supplier_id for s in repeated.suppliers) == sorted(
        s.supplier_id for s in package.suppliers
    )

    await expect(SourceUnavailableError, {f"{BASE}/sitemap.xml": SITEMAP_GOODS})
    await expect(SourceUnavailableError, {f"{BASE}/sitemap.xml": "не xml"})
    await expect(SourceUnavailableError, PAGES, failing=(f"{BASE}/price/010301-armatura",))
    await expect(
        SourceUnavailableError,
        {**PAGES, f"{BASE}/firms/010301-armatura?page=2": PULSCEN_FIRMS_PAGE},
    )
    await expect(BotProtectionError, {**PAGES, f"{BASE}/firms/010301-armatura": PULSCEN_BOT_CHECK})
    print("Проверка адаптера Пульс цен пройдена")


if __name__ == "__main__":
    asyncio.run(main())
