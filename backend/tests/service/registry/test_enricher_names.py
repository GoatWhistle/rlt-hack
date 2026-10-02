from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from src.models.enums import NameSource, SupplierRole
from src.models.package import SupplierPackage
from src.models.registry import MspCompany
from src.service.registry.enricher import SupplierRegistryEnricher
from tests.fakes.domain import make_source, make_supplier

NAMED = MspCompany(inn="7801234564", name="ООО «Альфа»", registry_date=date(2026, 9, 10))


class FakeRegistry:
    async def find(self, inns: Sequence[str]) -> dict[str, MspCompany]:
        return {inn: NAMED for inn in inns if inn == NAMED.inn}


class NoRoles:
    @property
    def version(self) -> str:
        return "test"

    def role_by_okved(self, code: str) -> SupplierRole | None:
        return None


async def test_missing_name_is_resolved_by_exact_inn_and_marked() -> None:
    blank = replace(make_supplier("alpha", inn=NAMED.inn), name="")
    other = replace(make_supplier("beta", inn="7707083893"), name="")
    named = make_supplier("gamma", inn=NAMED.inn)
    package = SupplierPackage(source=make_source(), suppliers=(blank, other, named))
    enriched = await SupplierRegistryEnricher(FakeRegistry(), NoRoles()).enrich(package)
    first, second, third = enriched.suppliers
    assert (first.name, first.name_source) == ("ООО «Альфа»", NameSource.REGISTRY)
    assert (second.name, second.name_source) == ("", NameSource.SOURCE)
    assert (third.name, third.name_source) == (named.name, NameSource.SOURCE)
