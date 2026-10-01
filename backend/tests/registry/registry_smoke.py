"""Проверка обогащения по реестру МСП без ClickHouse и сети.

Выгрузка собирается на лету из искусственного XML, хранилище и реестр заменены
заглушками, правила ролей берутся из настоящего справочника `reference/`.
"""

import asyncio
import sys
import tempfile
from datetime import date
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.adapter.client.errors import RegistryDumpError
from src.adapter.client.msp_registry import MspRegistryDump
from src.adapter.repository.reference import load_okved_roles
from src.models.enums import SourceType, SupplierRole
from src.models.package import SupplierPackage
from src.models.registry import MspCompany
from src.models.source import Source
from src.models.supplier import Supplier
from src.service.errors import EmptyRegistryDumpError
from src.service.registry import RegistryImportService, SupplierRegistryEnricher
from src.service.registry.roles import role_of
from tests.registry.fixtures import DOCUMENTS, EMPTY, write_zip

DAY = date(2026, 9, 10)


def company(inn: str, okved: str = "", products: tuple[str, ...] = ()) -> MspCompany:
    return MspCompany(inn=inn, name=inn, registry_date=DAY, okved_main=okved, products=products)


class FakeRegistry:
    def __init__(self, companies: list[MspCompany]) -> None:
        self._companies = {item.inn: item for item in companies}
        self.requests: list[list[str]] = []

    async def find(self, inns):
        self.requests.append(list(inns))
        return {inn: self._companies[inn] for inn in inns if inn in self._companies}


class FakeStore:
    def __init__(self) -> None:
        self.saved: list[MspCompany] = []
        self.calls = 0
        self.removed_before: date | None = None

    async def save_many(self, companies) -> None:
        self.saved.extend(companies)
        self.calls += 1

    async def remove_older(self, registry_date: date) -> None:
        self.removed_before = registry_date


async def check_roles() -> None:
    roles = await load_okved_roles()
    expected = {
        "46.49.3": SupplierRole.DISTRIBUTOR,
        "47.62": SupplierRole.RESELLER,
        "45.11": SupplierRole.RESELLER,
        "45.20": SupplierRole.SERVICE_PROVIDER,
        "17.12": SupplierRole.MANUFACTURER,
        "33.12": SupplierRole.SERVICE_PROVIDER,
        "62.01": SupplierRole.SERVICE_PROVIDER,
        "97.00": None,
    }
    for code, role in expected.items():
        assert roles.role_by_okved(code) == role, (code, roles.role_by_okved(code))

    role, evidence = role_of(company("7707049388", "46.76", ("17.12.14",)), roles)
    assert role == SupplierRole.MANUFACTURER, role
    assert "17.12.14" in evidence and "10.09.2026" in evidence, evidence
    assert role_of(company("7707049388"), roles) == (SupplierRole.UNKNOWN, "")
    assert role_of(company("7707049388", "99.00"), roles) == (SupplierRole.UNKNOWN, "")


async def check_enricher() -> None:
    roles = await load_okved_roles()
    registry = FakeRegistry(
        [
            MspCompany(
                inn="7804428656",
                name="ООО «КАНЦТОРГ»",
                registry_date=DAY,
                okved_main="46.49.3",
                okved_main_name="Торговля оптовая канцелярскими товарами",
                okved_extra=("47.62",),
            ),
            company("7707049388", "46.76"),
        ]
    )
    source = Source(
        source_id=UUID(int=1),
        name="Тест",
        base_url="https://test/",
        source_type=SourceType.DIRECTORY,
        provider_name="test",
    )
    suppliers = (
        Supplier(supplier_id=UUID(int=2), name="Канцторг", inn="7804428656"),
        # Роль и ОКВЭД источника не перезаписываются реестром.
        Supplier(
            supplier_id=UUID(int=3),
            name="Бумпром",
            inn="7707049388",
            okved_codes=("17.12",),
            role=SupplierRole.MANUFACTURER,
            role_evidence="карточка источника",
        ),
        Supplier(supplier_id=UUID(int=4), name="Вне реестра", inn="5003052454"),
        Supplier(supplier_id=UUID(int=5), name="Без ИНН"),
    )
    package = SupplierPackage(source=source, suppliers=suppliers)
    enriched = await SupplierRegistryEnricher(registry, roles).enrich(package)

    assert registry.requests == [["5003052454", "7707049388", "7804428656"]], registry.requests
    shop, factory, outside, anonymous = enriched.suppliers
    assert shop.role == SupplierRole.DISTRIBUTOR, shop
    assert shop.okved_codes == ("46.49.3", "47.62"), shop
    assert "«Торговля оптовая канцелярскими товарами»" in shop.role_evidence, shop
    assert factory == suppliers[1], factory
    assert outside == suppliers[2] and anonymous == suppliers[3]

    empty = SupplierPackage(source=source, suppliers=(suppliers[3],))
    assert await SupplierRegistryEnricher(registry, roles).enrich(empty) is empty
    assert len(registry.requests) == 1, "без ИНН реестр не запрашивается"


async def check_dump(directory: Path) -> None:
    path = write_zip(directory / "rmsp.zip", {"a.xml": DOCUMENTS, "readme.txt": "не XML"})
    batches = [batch async for batch in MspRegistryDump(path).read()]
    assert len(batches) == 1, batches
    by_inn = {item.inn: item for item in batches[0]}
    assert set(by_inn) == {"7804428656", "636200108061", "7707049388", "3728026176"}, by_inn
    shop = by_inn["7804428656"]
    assert shop.name == "ООО «КАНЦТОРГ»", shop
    assert shop.registry_date == DAY, shop
    assert shop.okved_main == "46.49.3", shop
    assert shop.okved_extra == ("47.62",), shop
    assert by_inn["636200108061"].name == "ИП Иванов Пётр Сергеевич", by_inn
    assert by_inn["7707049388"].products == ("17.12.14",), by_inn
    assert not shop.okved_main_reported, shop
    # Основного кода в сведениях реестра нет: он берётся из отчётности.
    clothes = by_inn["3728026176"]
    assert clothes.okved_main == "14.13" and clothes.okved_main_reported, clothes
    assert clothes.okved_extra == ("47.19",), clothes
    role, evidence = role_of(clothes, await load_okved_roles())
    assert role == SupplierRole.MANUFACTURER, role
    assert evidence.startswith("Основной ОКВЭД по отчётности 14.13"), evidence

    store = FakeStore()
    result = await RegistryImportService(MspRegistryDump(path), store).run()
    assert result.companies == 4 and result.registry_date == DAY, result
    assert store.removed_before == DAY, store.removed_before
    assert store.calls == 1, "мелкие пачки файлов копятся в одну вставку"

    two_files = write_zip(directory / "two.zip", {"a.xml": DOCUMENTS, "b.xml": DOCUMENTS})
    store = FakeStore()
    result = await RegistryImportService(MspRegistryDump(two_files), store, batch_size=4).run()
    assert result.companies == 8 and store.calls == 2, (result, store.calls)
    assert len(store.saved) == 8, store.saved

    # Пустая выгрузка не удаляет прежние сведения.
    empty = write_zip(directory / "empty.zip", {"a.xml": EMPTY})
    store = FakeStore()
    try:
        await RegistryImportService(MspRegistryDump(empty), store).run()
        raise AssertionError("пустая выгрузка принята")
    except EmptyRegistryDumpError:
        pass
    assert store.removed_before is None

    broken_xml = write_zip(directory / "broken.zip", {"a.xml": DOCUMENTS, "b.xml": "<Файл><Док"})
    store = FakeStore()
    await expect_dump_error(RegistryImportService(MspRegistryDump(broken_xml), store))
    assert store.removed_before is None, "оборванная загрузка удалила сведения"

    not_zip = directory / "not.zip"
    not_zip.write_text("<html>проверка доступа</html>", encoding="utf-8")
    await expect_dump_error(RegistryImportService(MspRegistryDump(not_zip), FakeStore()))
    no_xml = write_zip(directory / "noxml.zip", {"readme.txt": "пусто"})
    await expect_dump_error(RegistryImportService(MspRegistryDump(no_xml), FakeStore()))
    missing = directory / "missing.zip"
    await expect_dump_error(RegistryImportService(MspRegistryDump(missing), FakeStore()))


async def expect_dump_error(service: RegistryImportService) -> None:
    try:
        await service.run()
    except RegistryDumpError:
        return
    raise AssertionError("ошибка выгрузки не поднята")


async def main() -> None:
    await check_roles()
    await check_enricher()
    with tempfile.TemporaryDirectory(prefix="rlt-msp-") as temporary:
        await check_dump(Path(temporary))
    print("Проверка обогащения по реестру МСП пройдена")


if __name__ == "__main__":
    asyncio.run(main())
