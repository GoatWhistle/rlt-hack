"""Пересчёт нормализации и классификации у уже сохранённых позиций.

Тот же конвейер, что и при обходе источника, но вход берётся из хранилища:
правила и справочники меняются чаще, чем сами данные, поэтому производные
значения должны уметь пересчитываться отдельно от сбора. Сервис вызывает
нормализатор и классификатор через те же интерфейсы, что и обход.
"""

import logging

from src.models.coverage import CoverageReport
from src.models.enrichment import EnrichmentResult
from src.models.package import SupplierPackage
from src.service.supplier.protocols import (
    Clock,
    OfferCatalog,
    OfferClassifying,
    OfferNormalizing,
    SourceCatalog,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


class OfferEnrichmentService:
    def __init__(
        self,
        sources: SourceCatalog,
        offers: OfferCatalog,
        normalizer: OfferNormalizing,
        classifier: OfferClassifying,
        clock: Clock,
        batch_size: int = BATCH_SIZE,
    ) -> None:
        self._sources = sources
        self._offers = offers
        self._normalizer = normalizer
        self._classifier = classifier
        self._clock = clock
        self._batch_size = max(1, batch_size)

    async def run(self, limit: int | None = None) -> EnrichmentResult:
        """Обходит источники по одному: пакет источника задаёт контекст разбора."""
        processed = 0
        classified = 0
        touched_sources = 0
        for source in await self._sources.list_all():
            offset = 0
            seen = 0
            while limit is None or processed < limit:
                # Последняя пачка укорачивается до остатка лимита: лишние
                # позиции не читаются и не перезаписываются.
                size = (
                    self._batch_size if limit is None else min(self._batch_size, limit - processed)
                )
                batch = await self._offers.list_by_source(source.source_id, size, offset)
                if not batch:
                    break
                package = SupplierPackage(source=source, offers=tuple(batch))
                package = await self._normalizer.normalize(package)
                package = await self._classifier.classify(package)
                await self._offers.save_many(package.offers, self._clock.now())
                classified += sum(
                    1
                    for offer in package.offers
                    if offer.classification and offer.classification.okpd2_code
                )
                processed += len(batch)
                seen += len(batch)
                offset += len(batch)
            if seen:
                touched_sources += 1
                logger.info("Пересчитан источник %s: позиций — %d", source.provider_name, seen)
        return EnrichmentResult(
            sources=touched_sources,
            offers=processed,
            classified=classified,
            normalizer_version=self._normalizer.version,
            classifier_version=self._classifier.version,
        )

    async def coverage(self) -> CoverageReport:
        """Отчёт о покрытии читается из хранилища, а не считается заново."""
        return await self._offers.coverage()
