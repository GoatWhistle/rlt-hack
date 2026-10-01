"""Сервис синхронизации источников: конкурентный запуск адаптеров."""

import asyncio
import logging
from collections.abc import AsyncIterator
from uuid import uuid4

from src.models.enums import FetchStatus
from src.models.journal import CrawlRun, SourceSyncResult, SyncResult
from src.models.package import SupplierPackage
from src.service.supplier.batching import package_batches
from src.service.supplier.protocols import (
    Clock,
    CrawlJournal,
    OfferClassifying,
    OfferNormalizing,
    ResumableSupplierProvider,
    StreamingSupplierProvider,
    StreamingSupplierStorage,
    SupplierEnriching,
    SupplierProvider,
    SupplierStorage,
)

logger = logging.getLogger(__name__)


class SupplierSyncWorker:
    """Обходит все подключённые источники и сохраняет их пакеты.

    Адаптеры запускаются одновременно: медленный сайт не задерживает остальные,
    а сбой одного источника не отменяет чужие результаты. Число одновременных
    обходов ограничено, чтобы не упираться в сеть и запись в хранилище.

    Собранный пакет перед записью проходит обогащение компаний, нормализацию и
    классификацию: все три вызываются через интерфейс, их реализации сервису
    неизвестны.
    """

    def __init__(
        self,
        providers: list[SupplierProvider],
        storage: SupplierStorage,
        journal: CrawlJournal,
        clock: Clock,
        enricher: SupplierEnriching,
        normalizer: OfferNormalizing,
        classifier: OfferClassifying,
        interval_seconds: float = 3600.0,
        max_parallel_sources: int = 4,
        batch_size: int = 32,
    ) -> None:
        self._providers = providers
        self._storage = storage
        self._journal = journal
        self._clock = clock
        self._enricher = enricher
        self._normalizer = normalizer
        self._classifier = classifier
        self._interval = interval_seconds
        self._max_parallel_sources = max(1, max_parallel_sources)
        self._batch_size = max(1, batch_size)

    async def run_once(self) -> SyncResult:
        logger.info("Обход источников: подключено адаптеров — %d", len(self._providers))
        limit = asyncio.Semaphore(self._max_parallel_sources)
        results = await asyncio.gather(
            *(self._sync_guarded(provider, limit) for provider in self._providers)
        )
        return SyncResult(sources=tuple(results))

    async def run_forever(self) -> None:
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                logger.info("Синхронизация остановлена")
                raise
            except Exception:
                logger.exception("Итерация синхронизации не удалась")
            await asyncio.sleep(self._interval)

    async def sync_provider(self, provider: SupplierProvider) -> SourceSyncResult:
        """Обходит один источник. Сбой адаптера возвращается результатом."""
        source = provider.source
        started_at = self._clock.now()
        withdrawn = 0
        status = FetchStatus.SUCCESS
        error_message = ""
        package = SupplierPackage(source=source)
        supplier_ids = set()
        offer_ids = set()
        batched = isinstance(self._storage, StreamingSupplierStorage)
        try:
            if batched:
                observed_at = started_at
                if isinstance(provider, ResumableSupplierProvider):
                    observed_at = await provider.resume(started_at)
                async for package in self._batches(provider):
                    # Обогащение дополняет данные самого источника, поэтому идёт первым.
                    package = await self._enricher.enrich(package)
                    package = await self._normalizer.normalize(package)
                    package = await self._classifier.classify(package)
                    await self._storage.save_batch(package, observed_at)
                    supplier_ids.update(item.supplier_id for item in package.suppliers)
                    offer_ids.update(item.offer_id for item in package.offers)
                    logger.info(
                        "Источник %s: сохранён батч компаний %d и предложений %d,"
                        " всего компаний %d и предложений %d",
                        source.provider_name,
                        len(package.suppliers),
                        len(package.offers),
                        len(supplier_ids),
                        len(offer_ids),
                    )
                saved = (
                    provider.saved_offer_count
                    if isinstance(provider, ResumableSupplierProvider)
                    else 0
                )
                if offer_ids or saved:
                    withdrawn = await self._storage.finish_snapshot(source.source_id, observed_at)
                if isinstance(provider, ResumableSupplierProvider):
                    await provider.complete()
            else:
                package = await provider.fetch()
                package = await self._enricher.enrich(package)
                package = await self._normalizer.normalize(package)
                package = await self._classifier.classify(package)
                withdrawn = await self._storage.save_package(package)
                supplier_ids.update(item.supplier_id for item in package.suppliers)
                offer_ids.update(item.offer_id for item in package.offers)
        except Exception as error:
            status = FetchStatus.PARTIAL if supplier_ids or offer_ids else FetchStatus.FAILED
            error_message = f"{type(error).__name__}: {error}"
            logger.exception("Обход источника %s не удался", source.provider_name)
        run = CrawlRun(
            run_id=uuid4(),
            source_id=source.source_id,
            started_at=started_at,
            finished_at=self._clock.now(),
            status=status,
            suppliers_extracted=len(supplier_ids),
            offers_extracted=len(offer_ids),
            provider_name=source.provider_name,
            error_message=error_message,
        )
        try:
            await self._journal.save_run(run)
        except Exception:
            # Журнал не влияет на собранные данные: они уже сохранены.
            logger.exception("Журнал обхода не обновлён для %s", source.provider_name)
        return SourceSyncResult(
            provider_name=source.provider_name,
            status=status,
            source_id=source.source_id,
            suppliers_extracted=len(supplier_ids),
            offers_extracted=len(offer_ids),
            offers_withdrawn=withdrawn,
            error_message=error_message,
        )

    async def _batches(self, provider: SupplierProvider) -> AsyncIterator[SupplierPackage]:
        """Порции источника: потоковый адаптер отдаёт их сам, остальные делятся здесь.

        Деление собранного пакета не делает обход потоковым: адаптер всё равно
        держит его в памяти целиком. Оно выравнивает порции разбора и записи,
        чтобы все источники шли через хранилище одинаково.
        """
        if isinstance(provider, StreamingSupplierProvider):
            async for package in provider.batches(self._batch_size):
                yield package
            return
        package = await provider.fetch()
        for batch in package_batches(package, self._batch_size):
            yield batch

    async def _sync_guarded(
        self,
        provider: SupplierProvider,
        limit: asyncio.Semaphore,
    ) -> SourceSyncResult:
        async with limit:
            return await self.sync_provider(provider)
