"""Репозиторий пакета источника: источник, его компании и предложения.

Пакет — полное состояние источника на момент обхода, поэтому он сохраняется
одной операцией: строки пишутся полным снимком новой версией, а предложения
источника, которых в пакете нет, снимаются с продажи. Снятие не удаляет данные:
они остаются со статусом недоступности.
"""

import dataclasses
import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from uuid import UUID

from src.adapter.repository.clickhouse.offer import ClickHouseOfferRepository
from src.adapter.repository.clickhouse.source import ClickHouseSourceRepository
from src.adapter.repository.clickhouse.supplier import ClickHouseSupplierRepository
from src.models.offer import Offer
from src.models.package import SupplierPackage
from src.models.supplier import Supplier

logger = logging.getLogger(__name__)


class ClickHousePackageRepository:
    def __init__(
        self,
        sources: ClickHouseSourceRepository,
        suppliers: ClickHouseSupplierRepository,
        offers: ClickHouseOfferRepository,
        batch_size: int = 500,
    ) -> None:
        self._sources = sources
        self._suppliers = suppliers
        self._offers = offers
        self._batch_size = max(1, batch_size)

    async def save_package(self, package: SupplierPackage) -> int:
        """Отметка обхода одна на пакет: по ней отбираются исчезнувшие предложения."""
        observed_at = datetime.now(UTC)
        await self._sources.save_many([package.source])
        for batch in _batches(_unique_suppliers(package.suppliers), self._batch_size):
            await self._suppliers.save_many(batch)
        offers = _unique_offers(package.offers)
        # Время первой встречи читается один раз на пакет: список его предложений
        # слишком велик, чтобы передавать идентификаторы параметром запроса.
        known = await self._offers.first_seen(package.source.source_id)
        for batch in _batches(offers, self._batch_size):
            await self._save_offers(batch, known, observed_at)
        if not offers:
            # Пустой пакет чаще означает сломанный разбор, чем исчезновение всего
            # ассортимента: снимать предложения с продажи в этом случае нельзя.
            return 0
        return await self._offers.withdraw_absent(package.source.source_id, observed_at)

    async def save_batch(self, package: SupplierPackage, observed_at: datetime) -> None:
        await self._sources.save_many([package.source])
        for batch in _batches(_unique_suppliers(package.suppliers), self._batch_size):
            await self._suppliers.save_many(batch)
        for batch in _batches(_unique_offers(package.offers), self._batch_size):
            known = await self._offers.first_seen_for([offer.offer_id for offer in batch])
            await self._save_offers(batch, known, observed_at)

    async def finish_snapshot(self, source_id: UUID, observed_at: datetime) -> int:
        return await self._offers.withdraw_absent(source_id, observed_at)

    async def _save_offers(
        self,
        offers: Sequence[Offer],
        known: Mapping[UUID, datetime],
        observed_at: datetime,
    ) -> None:
        """Время первой встречи не теряется: новая версия строки его сохраняет."""
        stored = [
            dataclasses.replace(
                offer,
                first_seen_at=min(
                    offer.first_seen_at,
                    known.get(offer.offer_id, offer.first_seen_at),
                ),
            )
            for offer in offers
        ]
        await self._offers.save_many(stored, observed_at)


def _batches[T](items: Sequence[T], size: int) -> list[Sequence[T]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _unique_suppliers(suppliers: Sequence[Supplier]) -> list[Supplier]:
    """Компания встречается в пакете много раз: последняя запись выигрывает."""
    unique: dict[UUID, Supplier] = {item.supplier_id: item for item in suppliers}
    return list(unique.values())


def _unique_offers(offers: Sequence[Offer]) -> list[Offer]:
    unique: dict[UUID, Offer] = {}
    for offer in offers:
        previous = unique.get(offer.offer_id)
        if previous is None or offer.last_seen_at >= previous.last_seen_at:
            unique[offer.offer_id] = offer
    return list(unique.values())
