"""Крупная пачка записи: список идентификаторов не ломает запрос.

`first_seen_for` перечисляет идентификаторы в запросе, а его длину ограничивает
`max_query_size` ClickHouse. Проверяется пачка больше `ID_QUERY_LIMIT`: запрос
должен делиться на части и возвращать время первой встречи для всех строк.
"""

import asyncio
import sys
import tempfile
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from chdb.session import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapter.repository.clickhouse.migrator import Migrator
from src.adapter.repository.clickhouse.offer import (
    ID_QUERY_LIMIT,
    ClickHouseOfferRepository,
)
from src.adapter.repository.clickhouse.package import ClickHousePackageRepository
from src.adapter.repository.clickhouse.source import ClickHouseSourceRepository
from src.adapter.repository.clickhouse.supplier import ClickHouseSupplierRepository
from src.adapter.repository.clickhouse.versions import VersionSequencer
from src.models.enums import ItemType, SourceType, VerificationStatus
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.source import Source
from src.models.supplier import Supplier
from src.service.supplier.batching import package_batches
from tests.clickhouse.chdb_gateway import ChdbGateway

FIRST = datetime(2026, 10, 1, 12, tzinfo=UTC)
LATER = FIRST + timedelta(days=1)
SOURCE = Source(
    source_id=UUID("00000000-0000-0000-0000-0000000000b1"),
    name="Крупный источник",
    base_url="https://bulk.test/",
    source_type=SourceType.REGISTRY,
    provider_name="bulk",
)


def make_package(count: int, moment: datetime) -> SupplierPackage:
    supplier = Supplier(UUID("00000000-0000-0000-0000-0000000000b2"), "ООО Поставщик")
    offers = tuple(
        Offer(
            offer_id=UUID(int=index + 1),
            source_id=SOURCE.source_id,
            external_id=str(index),
            url=f"https://bulk.test/{index}",
            name=f"Позиция {index}",
            first_seen_at=moment,
            last_seen_at=moment,
            supplier_id=supplier.supplier_id,
            seller_status=VerificationStatus.UNVERIFIED,
            item_type=ItemType.GOODS,
            content_hash=f"hash-{index}",
        )
        for index in range(count)
    )
    return SupplierPackage(SOURCE, (supplier,), offers)


# Запрос обязан превысить max_query_size (256 КиБ) без деления, иначе проверка
# подтвердит только полноту результата, но не сам предел: UUID в тексте запроса
# занимает 38 байт, поэтому порог около 6 800 идентификаторов.
UUID_IN_QUERY = 38
OVER_LIMIT = 256 * 1024 // UUID_IN_QUERY + 1200


async def check() -> None:
    count = OVER_LIMIT
    assert count * UUID_IN_QUERY > 256 * 1024, "Пачка должна превышать предел запроса"
    assert count > ID_QUERY_LIMIT, "Пачка должна делиться на части"
    with tempfile.TemporaryDirectory(prefix="rlt-offer-batch-") as directory:
        session = cast("Callable[[str], Any]", Session)(str(Path(directory) / "db"))
        try:
            gateway = ChdbGateway(session)
            await Migrator(gateway).apply_pending()
            versions = VersionSequencer()
            offers = ClickHouseOfferRepository(gateway, versions)
            storage = ClickHousePackageRepository(
                sources=ClickHouseSourceRepository(gateway, versions),
                suppliers=ClickHouseSupplierRepository(gateway, versions),
                offers=offers,
                batch_size=count,
            )

            # Одна пачка на весь пакет: столько идентификаторов в запрос не влезает.
            package = make_package(count, FIRST)
            for part in package_batches(package, count):
                await storage.save_batch(part, FIRST)

            ids = [offer.offer_id for offer in package.offers]
            known = await offers.first_seen_for(ids)
            assert len(known) == count, len(known)
            assert set(known) == set(ids), "Ни один идентификатор не потерян при делении"
            assert all(value == FIRST for value in known.values()), "Время первой встречи"

            # Повторный обход не сдвигает first_seen, хотя строки переписаны заново.
            repeated = replace(
                package,
                offers=tuple(
                    replace(offer, first_seen_at=LATER, last_seen_at=LATER)
                    for offer in package.offers
                ),
            )
            for part in package_batches(repeated, count):
                await storage.save_batch(part, LATER)
            after = await offers.first_seen_for(ids)
            assert len(after) == count, len(after)
            assert all(value == FIRST for value in after.values()), "first_seen сохраняется"

            # Пустой список запросов не делает.
            assert await offers.first_seen_for([]) == {}
        finally:
            session.cleanup()


if __name__ == "__main__":
    asyncio.run(check())
    print("Крупная пачка записи: проверки прошли")
