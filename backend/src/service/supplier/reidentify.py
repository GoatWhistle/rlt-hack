"""Перевод сохранённых предложений на действующее правило ключа.

Ключ источника определяет `offer_id`, а на нём висит вся история: время первой
встречи, версии строки, снятие с продажи. Поэтому смена правила — не правка
парсера, а отдельная операция с переносом: позиция получает новый ID, но
сохраняет время первой встречи, а строка под старым ID помечается удалённой.

Старые строки отбираются по отметке перезаписи, а не списком идентификаторов:
их тысячи, и в параметры запроса они не помещаются. Для этого переписываются
все позиции источника, включая те, у которых ключ не изменился.
"""

import dataclasses
import logging
from uuid import UUID

from src.models.enrichment import ReidentifyResult
from src.models.offer import Offer
from src.service.supplier.protocols import (
    Clock,
    OfferCatalog,
    OfferIdentity,
    SourceCatalog,
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 500


class OfferReidentifyService:
    def __init__(
        self,
        sources: SourceCatalog,
        offers: OfferCatalog,
        identity: OfferIdentity,
        clock: Clock,
        page_size: int = PAGE_SIZE,
    ) -> None:
        self._sources = sources
        self._offers = offers
        self._identity = identity
        self._clock = clock
        self._page_size = max(1, page_size)

    async def run(self) -> ReidentifyResult:
        changed = 0
        merged = 0
        processed = 0
        touched = 0
        for source in await self._sources.list_all():
            stored = await self._read_all(source.source_id)
            if not stored:
                continue
            rekeyed, source_changed, source_merged = self._rekey(stored)
            written_at = self._clock.now()
            await self._offers.save_many(rekeyed, written_at)
            removed = await self._offers.delete_stale(source.source_id, written_at)
            processed += len(stored)
            changed += source_changed
            merged += source_merged
            touched += 1
            logger.info(
                "Источник %s: позиций — %d, сменили ключ — %d, слились — %d, снято старых — %d",
                source.provider_name,
                len(stored),
                source_changed,
                source_merged,
                removed,
            )
        return ReidentifyResult(sources=touched, offers=processed, changed=changed, merged=merged)

    def _rekey(self, offers: list[Offer]) -> tuple[list[Offer], int, int]:
        """Считает новые ключи и сводит позиции, которые стали одной.

        Две позиции одной страницы могли отличаться только оформлением
        названия: после перехода на отпечаток они становятся одной записью, и
        побеждает самая ранняя встреча.
        """
        unique: dict[str, Offer] = {}
        changed = 0
        merged = 0
        for offer in offers:
            external_id = self._identity.rekey(offer.external_id, offer.url, offer.name)
            offer_id = self._identity.offer_id(offer.source_id, external_id)
            if offer_id != offer.offer_id:
                changed += 1
            updated = dataclasses.replace(offer, offer_id=offer_id, external_id=external_id)
            previous = unique.get(external_id)
            if previous is None:
                unique[external_id] = updated
                continue
            merged += 1
            unique[external_id] = dataclasses.replace(
                updated,
                first_seen_at=min(previous.first_seen_at, updated.first_seen_at),
                last_seen_at=max(previous.last_seen_at, updated.last_seen_at),
            )
        return list(unique.values()), changed, merged

    async def _read_all(self, source_id: UUID) -> list[Offer]:
        """Позиции источника читаются целиком: писать и листать одновременно нельзя."""
        offers: list[Offer] = []
        offset = 0
        while True:
            page = await self._offers.list_by_source(source_id, self._page_size, offset)
            if not page:
                return offers
            offers.extend(page)
            offset += len(page)
