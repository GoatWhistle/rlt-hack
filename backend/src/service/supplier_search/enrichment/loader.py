import asyncio
import logging
from collections.abc import Awaitable, Mapping, Sequence
from uuid import UUID

from src.models.company.offer_evidence import OfferEvidence
from src.models.enums import EnrichmentSource, WarningCode
from src.models.search.query_item import QueryItem
from src.models.search.search_result import SearchWarning
from src.service.supplier_search.enrichment.bundle import Enrichment
from src.service.supplier_search.fusion.candidate import FusedCandidate
from src.service.supplier_search.protocols import OfferCatalog, PurchaseHistory, SupplierDirectory
from src.service.supplier_search.settings import SearchSettings

logger = logging.getLogger(__name__)

DIRECTORY = EnrichmentSource.DIRECTORY
OFFERS = EnrichmentSource.OFFERS
CURRENT_OFFERS = EnrichmentSource.CURRENT_OFFERS
HISTORY = EnrichmentSource.HISTORY

CurrentIds = Mapping[UUID, tuple[UUID, ...]]
Cards = Mapping[UUID, OfferEvidence]


async def _attempt[K, V](source: str, call: Awaitable[Mapping[K, V]]) -> Mapping[K, V] | None:
    try:
        return await call
    except Exception:
        logger.warning("enrichment source failed", extra={"source": source}, exc_info=True)
        return None


def _current(ids: CurrentIds | None, cards: Cards | None) -> dict[UUID, tuple[OfferEvidence, ...]]:
    if ids is None or cards is None:
        return {}
    found = {
        supplier_id: tuple(cards[offer_id] for offer_id in offer_ids if offer_id in cards)
        for supplier_id, offer_ids in ids.items()
    }
    return {supplier_id: owned for supplier_id, owned in found.items() if owned}


class EnrichmentLoader:
    def __init__(
        self,
        directory: SupplierDirectory,
        offers: OfferCatalog,
        history: PurchaseHistory,
        settings: SearchSettings,
    ) -> None:
        self._directory = directory
        self._offers = offers
        self._history = history
        self._settings = settings

    async def load(
        self, candidates: Sequence[FusedCandidate], items: Sequence[QueryItem]
    ) -> tuple[Enrichment, tuple[SearchWarning, ...]]:
        supplier_ids = [candidate.supplier_id for candidate in candidates]
        referenced = list(
            dict.fromkeys(offer_id for candidate in candidates for offer_id in candidate.offer_ids)
        )
        suppliers, (offers, current), histories = await asyncio.gather(
            _attempt(DIRECTORY, self._directory.get_many(supplier_ids)),
            self._load_offers(supplier_ids, referenced),
            _attempt(
                HISTORY,
                self._history.summarize(supplier_ids, items, self._settings.history_records),
            ),
        )
        outcomes = {
            DIRECTORY: suppliers,
            OFFERS: offers,
            CURRENT_OFFERS: current,
            HISTORY: histories,
        }
        failed = frozenset(source for source, value in outcomes.items() if value is None)
        enrichment = Enrichment(
            suppliers=suppliers or {},
            offers=offers or {},
            current=current or {},
            histories=histories or {},
            failed=failed,
        )
        warnings = tuple(
            SearchWarning(WarningCode.ENRICHMENT_FAILED, source)
            for source in outcomes
            if source in failed
        )
        return enrichment, warnings

    async def _load_offers(
        self, supplier_ids: Sequence[UUID], referenced: Sequence[UUID]
    ) -> tuple[Cards | None, Mapping[UUID, tuple[OfferEvidence, ...]] | None]:
        per_supplier = self._settings.offers_per_supplier
        ids = await _attempt(CURRENT_OFFERS, self._offers.current_ids(supplier_ids, per_supplier))
        current_ids = [offer_id for owned in (ids or {}).values() for offer_id in owned]
        wanted = list(dict.fromkeys((*referenced, *current_ids)))
        cards = await _attempt(OFFERS, self._cards(wanted))
        offers = None if cards is None else {key: cards[key] for key in referenced if key in cards}
        current = None if ids is None or cards is None else _current(ids, cards)
        return offers, current

    async def _cards(self, offer_ids: Sequence[UUID]) -> Cards:
        if not offer_ids:
            return {}
        return await self._offers.get_many(offer_ids)
