"""Сервис синхронизации источников: конкурентный запуск адаптеров."""

import asyncio
import logging
from uuid import uuid4

from src.models.enums import FetchStatus
from src.models.journal import CrawlRun, SourceSyncResult, SyncResult
from src.models.package import SupplierPackage
from src.service.supplier.protocols import (
    Clock,
    CrawlJournal,
    OfferClassifying,
    OfferNormalizing,
    SupplierProvider,
    SupplierStorage,
)

logger = logging.getLogger(__name__)


class SupplierSyncWorker:
    """Обходит все подключённые источники и сохраняет их пакеты.

    Адаптеры запускаются одновременно: медленный сайт не задерживает остальные,
    а сбой одного источника не отменяет чужие результаты. Число одновременных
    обходов ограничено, чтобы не упираться в сеть и запись в хранилище.

    Собранный пакет перед записью проходит нормализацию и классификацию: обе
    вызываются через интерфейс, их реализации сервису неизвестны.
    """

    def __init__(
        self,
        providers: list[SupplierProvider],
        storage: SupplierStorage,
        journal: CrawlJournal,
        clock: Clock,
        normalizer: OfferNormalizing,
        classifier: OfferClassifying,
        interval_seconds: float = 3600.0,
        max_parallel_sources: int = 4,
    ) -> None:
        self._providers = providers
        self._storage = storage
        self._journal = journal
        self._clock = clock
        self._normalizer = normalizer
        self._classifier = classifier
        self._interval = interval_seconds
        self._max_parallel_sources = max(1, max_parallel_sources)

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
        try:
            package = await provider.fetch()
            # Классификатору нужно нормализованное название, поэтому порядок
            # шагов задан здесь, а не в реализациях.
            package = await self._normalizer.normalize(package)
            package = await self._classifier.classify(package)
            withdrawn = await self._storage.save_package(package)
            logger.info(
                "Источник %s: компаний — %d, предложений — %d, снято с продажи — %d",
                source.provider_name,
                len(package.suppliers),
                len(package.offers),
                withdrawn,
            )
        except Exception as error:
            status = FetchStatus.FAILED
            error_message = f"{type(error).__name__}: {error}"
            logger.exception("Обход источника %s не удался", source.provider_name)
        run = CrawlRun(
            run_id=uuid4(),
            source_id=source.source_id,
            started_at=started_at,
            finished_at=self._clock.now(),
            status=status,
            suppliers_extracted=len(package.suppliers),
            offers_extracted=len(package.offers),
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
            suppliers_extracted=len(package.suppliers),
            offers_extracted=len(package.offers),
            offers_withdrawn=withdrawn,
            error_message=error_message,
        )

    async def _sync_guarded(
        self,
        provider: SupplierProvider,
        limit: asyncio.Semaphore,
    ) -> SourceSyncResult:
        async with limit:
            return await self.sync_provider(provider)
