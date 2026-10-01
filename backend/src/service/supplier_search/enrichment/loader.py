import asyncio
import logging
from collections.abc import Awaitable, Mapping, Sequence
from uuid import UUID

from src.models.enums import WarningCode
from src.models.offer_evidence import OfferEvidence
from src.models.query_item import QueryItem
from src.models.search_result import SearchWarning
from src.service.supplier_search.enrichment.bundle import Enrichment
from src.service.supplier_search.fusion.candidate import FusedCandidate
from src.service.supplier_search.protocols import OfferCatalog, PurchaseHistory, SupplierDirectory
from src.service.supplier_search.settings import SearchSettings

logger = logging.getLogger(__name__)

DIRECTORY = "directory"
OFFERS = "offers"
CURRENT_OFFERS = "currentOffers"
HISTORY = "history"


async def _attempt[K, V](source: str, call: Awaitable[Mapping[K, V]]) -> Mapping[K, V] | None:
    try:
        return await call
    except Exception:
        logger.warning("enrichment source failed", extra={"source": source}, exc_info=True)
        return None


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
        offer_ids = list(
            dict.fromkeys(offer_id for candidate in candidates for offer_id in candidate.offer_ids)
        )
        suppliers, offers, current, histories = await asyncio.gather(
            _attempt(DIRECTORY, self._directory.get_many(supplier_ids)),
            _attempt(OFFERS, self._load_offers(offer_ids)),
            _attempt(
                CURRENT_OFFERS,
                self._offers.current_for(supplier_ids, self._settings.offers_per_supplier),
            ),
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

    async def _load_offers(self, offer_ids: Sequence[UUID]) -> Mapping[UUID, OfferEvidence]:
        if not offer_ids:
            return {}
        return await self._offers.get_many(offer_ids)
