"""Проверка полного локального снимка публичных JSON-перечней ГИСП."""

import asyncio
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.supplier import identity
from src.adapter.supplier.errors import ContentFormatError
from src.adapter.supplier.gisp_registry import GispRegistryProvider
from src.models.catalog.source import Source
from src.models.enums import SourceType

BASE = "https://gisp.gov.ru/pp719v2/pub/prod/"
SOURCE = Source(
    identity.source_id(BASE, "gisp_registry"), "ГИСП", BASE, SourceType.REGISTRY, "gisp_registry"
)


def write_snapshot(
    directory: Path, products: list[dict], repeat_organization: bool = False
) -> None:
    organizations = [
        {"org_name": "ООО Завод", "org_inn": "7707083893", "org_region_name": "Москва"},
        {"org_name": "ООО Без продукции", "org_inn": "4707019370"},
    ]
    if repeat_organization:
        organizations.append(organizations[0])
    manifest = {"format": "gisp-browser-snapshot-v1"}
    for name, rows in (("organizations", organizations), ("products", products)):
        content = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows).encode()
        (directory / f"{name}.jsonl").write_bytes(content)
        manifest[name] = {"count": len(rows), "sha256": hashlib.sha256(content).hexdigest()}
    (directory / "manifest.json").write_text(json.dumps(manifest))


async def checks() -> None:
    products = [
        {
            "_org_name": "ООО Завод",
            "_org_inn": "7707083893",
            "_product_reg_number_2023": "10001",
            "_product_name": "Станок",
            "_res_date": "2026-01-01",
            "_res_valid_till": "2028-01-01",
            "_res_scan_url": f"https://gisp.gov.ru/document/{index}",
        }
        for index in (1, 2)
    ]
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        write_snapshot(directory, products)
        provider = GispRegistryProvider(SOURCE, directory.as_uri())
        package = await provider.fetch()
        assert len(package.suppliers) == 2
        assert len(package.offers) == 2
        assert len({offer.offer_id for offer in package.offers}) == 2
        assert {offer.supplier_id for offer in package.offers} == {
            next(
                supplier.supplier_id
                for supplier in package.suppliers
                if supplier.inn == "7707083893"
            )
        }
        assert {offer.offer_id for offer in (await provider.fetch()).offers} == {
            offer.offer_id for offer in package.offers
        }
        with (directory / "products.jsonl").open("ab") as stream:
            stream.write(b"{}\n")
        try:
            await provider.fetch()
        except ContentFormatError:
            pass
        else:
            raise AssertionError("Дополненный без манифеста снимок не должен сохраняться")
        write_snapshot(directory, [products[0], products[0]])
        try:
            await provider.fetch()
        except ContentFormatError as error:
            assert "повтор записи продукции" in str(error)
        else:
            raise AssertionError("Повтор записи не должен сохранять неполный снимок")
        write_snapshot(directory, products, repeat_organization=True)
        try:
            await provider.fetch()
        except ContentFormatError as error:
            assert "повтор организации" in str(error)
        else:
            raise AssertionError("Повтор организации не должен сохранять неполный снимок")


if __name__ == "__main__":
    asyncio.run(checks())
    print("ГИСП snapshot: проверки прошли")
