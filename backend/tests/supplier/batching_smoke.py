"""Деление собранного пакета на порции: состав, порядок и пустой обход."""

import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.models.enums import ItemType, SourceType, VerificationStatus
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier
from src.service.supplier.batching import package_batches

NOW = datetime(2026, 10, 2, 12, tzinfo=UTC)
SOURCE = Source(
    source_id=UUID("00000000-0000-0000-0000-0000000000a1"),
    name="Тестовый источник",
    base_url="https://example.test/",
    source_type=SourceType.DIRECTORY,
    provider_name="test",
)


def supplier(index: int) -> Supplier:
    return Supplier(
        supplier_id=UUID(f"00000000-0000-0000-0000-0000000001{index:02d}"),
        name=f"Компания {index}",
    )


def offer(index: int, owner: int) -> Offer:
    return Offer(
        offer_id=UUID(f"00000000-0000-0000-0000-0000000002{index:02d}"),
        source_id=SOURCE.source_id,
        external_id=f"offer-{index}",
        url=f"https://example.test/offer/{index}",
        name=f"Позиция {index}",
        first_seen_at=NOW,
        last_seen_at=NOW,
        supplier_id=supplier(owner).supplier_id,
        seller_status=VerificationStatus.UNVERIFIED,
        item_type=ItemType.GOODS,
        content_hash=f"hash-{index}",
    )


def main() -> None:
    package = SupplierPackage(
        source=SOURCE,
        suppliers=tuple(supplier(i) for i in range(3)),
        offers=tuple(offer(i, i % 3) for i in range(7)),
    )
    batches = list(package_batches(package, 2))

    # Компании идут первыми и отдельно: обогащение работает только с ними.
    assert [len(batch.suppliers) for batch in batches] == [2, 1, 0, 0, 0, 0], batches
    assert [len(batch.offers) for batch in batches] == [0, 0, 2, 2, 2, 1], batches
    assert all(batch.source == SOURCE for batch in batches), "Паспорт источника в каждой порции"

    # Ни одна сущность не теряется и не повторяется.
    assert [s.supplier_id for b in batches for s in b.suppliers] == [
        supplier(i).supplier_id for i in range(3)
    ]
    assert [o.offer_id for b in batches for o in b.offers] == [
        offer(i, i % 3).offer_id for i in range(7)
    ]

    # Порция целиком помещается в один батч, если он больше пакета.
    whole = list(package_batches(package, 100))
    assert [len(b.suppliers) for b in whole] == [3, 0] and [len(b.offers) for b in whole] == [0, 7]

    # Пустой обход отдаёт одну пустую порцию: он успешен, но данных не принёс.
    empty = list(package_batches(SupplierPackage(source=SOURCE), 10))
    assert len(empty) == 1 and not empty[0].suppliers and not empty[0].offers, empty

    # Источник без компаний, но с предложениями, и наоборот.
    only_offers = list(package_batches(SupplierPackage(source=SOURCE, offers=package.offers), 3))
    assert [len(b.offers) for b in only_offers] == [3, 3, 1], only_offers
    only_suppliers = list(
        package_batches(SupplierPackage(source=SOURCE, suppliers=package.suppliers), 3)
    )
    assert [len(b.suppliers) for b in only_suppliers] == [3], only_suppliers

    for size in (0, -1):
        try:
            list(package_batches(package, size))
        except ValueError:
            continue
        raise AssertionError("Неположительный размер порции должен отклоняться")


if __name__ == "__main__":
    main()
    print("Деление пакета на порции: проверки прошли")
