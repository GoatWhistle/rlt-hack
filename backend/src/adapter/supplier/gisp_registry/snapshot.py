"""Чтение полного локального снимка публичных перечней ГИСП."""

import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from src.adapter.supplier.errors import ContentFormatError, SourceUnavailableError
from src.adapter.supplier.gisp_registry.api import parse_organization, parse_product
from src.adapter.supplier.gisp_registry.supplier import merge_supplier
from src.models.catalog.offer import Offer
from src.models.catalog.package import SupplierPackage
from src.models.catalog.source import Source
from src.models.catalog.supplier import Supplier

FORMAT = "gisp-browser-snapshot-v1"


def _rows(directory: Path, name: str, expected: dict) -> Iterator[dict[str, object]]:
    path = directory / f"{name}.jsonl"
    digest = hashlib.sha256()
    count = 0
    try:
        with path.open("rb") as stream:
            for number, line in enumerate(stream, start=1):
                digest.update(line)
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ContentFormatError(f"ГИСП {name}: строка {number} не является объектом")
                count = number
                yield item
    except OSError as error:
        raise SourceUnavailableError(f"ГИСП {name}: {error}") from error
    except json.JSONDecodeError as error:
        raise ContentFormatError(f"ГИСП {name}: неверный JSON: {error}") from error
    if count != expected.get("count") or digest.hexdigest() != expected.get("sha256"):
        raise ContentFormatError(f"ГИСП {name}: число строк или хеш не совпадает с манифестом")


def parse_snapshot(directory: Path, source: Source) -> SupplierPackage:
    try:
        manifest = json.loads((directory / "manifest.json").read_text())
    except OSError as error:
        raise SourceUnavailableError(f"ГИСП: манифест недоступен: {error}") from error
    except json.JSONDecodeError as error:
        raise ContentFormatError(f"ГИСП: неверный манифест: {error}") from error
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
        raise ContentFormatError("ГИСП: неизвестный формат снимка")
    organization_meta = manifest.get("organizations")
    product_meta = manifest.get("products")
    for name, meta in (("organizations", organization_meta), ("products", product_meta)):
        if not isinstance(meta, dict) or not isinstance(meta.get("count"), int):
            raise ContentFormatError(f"ГИСП {name}: неверное число строк в манифесте")
        if meta["count"] <= 0 or not isinstance(meta.get("sha256"), str):
            raise ContentFormatError(f"ГИСП {name}: неполный манифест")
    suppliers: dict[UUID, Supplier] = {}
    offers: dict[str, Offer] = {}
    for item in _rows(directory, "organizations", organization_meta):
        supplier = parse_organization(item, source)
        if supplier.supplier_id in suppliers:
            raise ContentFormatError(f"ГИСП: повтор организации {supplier.supplier_id}")
        suppliers[supplier.supplier_id] = supplier
    observed_at = datetime.now(UTC)
    for item in _rows(directory, "products", product_meta):
        supplier, offer = parse_product(item, source, observed_at)
        previous_supplier = suppliers.get(supplier.supplier_id)
        suppliers[supplier.supplier_id] = (
            merge_supplier(previous_supplier, supplier) if previous_supplier else supplier
        )
        previous_offer = offers.get(offer.external_id)
        if previous_offer:
            raise ContentFormatError(f"ГИСП: повтор записи продукции {offer.external_id}")
        offers[offer.external_id] = offer
    return SupplierPackage(
        source=source,
        suppliers=tuple(suppliers.values()),
        offers=tuple(offers.values()),
    )
