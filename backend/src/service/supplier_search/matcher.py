import dataclasses
import logging
from collections.abc import Sequence

from src.models.archive_roster import ArchiveRoster
from src.models.candidate import SupplierCandidate
from src.models.enums import EnrichmentSource, WarningCode
from src.models.match import MatchOutcome
from src.models.query_item import SearchRequest
from src.models.search_result import SearchWarning
from src.service.supplier_search.assembly.assembler import CandidateAssembler
from src.service.supplier_search.enrichment.loader import EnrichmentLoader
from src.service.supplier_search.fusion.candidate import FusedCandidate
from src.service.supplier_search.fusion.rrf import ReciprocalRankFusion
from src.service.supplier_search.policy.policy import CandidatePolicy
from src.service.supplier_search.protocols import (
    ArchiveRosterReading,
    CandidateRetriever,
    OfferCatalog,
    PurchaseHistory,
    SupplierDirectory,
)
from src.service.supplier_search.ranking.ranker import CandidateRanker
from src.service.supplier_search.retrieval.runner import ChannelRunner
from src.service.supplier_search.settings import SearchSettings

logger = logging.getLogger(__name__)

ARCHIVE_FAILED = SearchWarning(WarningCode.ENRICHMENT_FAILED, EnrichmentSource.ARCHIVE)


class SupplierMatcher:
    def __init__(
        self,
        retrievers: Sequence[CandidateRetriever],
        directory: SupplierDirectory,
        offers: OfferCatalog,
        history: PurchaseHistory,
        fusion: ReciprocalRankFusion,
        assembler: CandidateAssembler,
        policy: CandidatePolicy,
        ranker: CandidateRanker,
        settings: SearchSettings,
        roster: ArchiveRosterReading | None = None,
    ) -> None:
        self._channels = ChannelRunner(retrievers)
        self._enrichment = EnrichmentLoader(directory, offers, history, settings)
        self._fusion = fusion
        self._assembler = assembler
        self._policy = policy
        self._ranker = ranker
        self._settings = settings
        self._roster = roster

    async def match(self, request: SearchRequest) -> MatchOutcome:
        depth = self._settings.retrieval_depth(request.query.limit.value)
        hits, channel_warnings = await self._channels.run(request, depth)
        fused = self._fusion.fuse(hits)[:depth]
        candidates, enrichment_warnings = await self._candidates(fused, request)
        roster, roster_warnings = await self._load_roster(candidates)
        return MatchOutcome(
            candidates=_with_novelty(candidates, roster),
            channels=tuple(channel.channel for channel in hits),
            warnings=(*channel_warnings, *enrichment_warnings, *roster_warnings),
            novelty_set="" if roster is None else roster.version,
        )

    async def _candidates(
        self, fused: Sequence[FusedCandidate], request: SearchRequest
    ) -> tuple[tuple[SupplierCandidate, ...], tuple[SearchWarning, ...]]:
        if not fused:
            return (), ()
        enrichment, warnings = await self._enrichment.load(fused, request.items)
        drafts = (self._assembler.assemble(entry, request.items, enrichment) for entry in fused)
        judged = [(draft, self._policy.evaluate(draft)) for draft in drafts if draft is not None]
        return self._ranker.rank(judged, request.query.limit.value), warnings

    async def _load_roster(
        self, candidates: Sequence[SupplierCandidate]
    ) -> tuple[ArchiveRoster | None, tuple[SearchWarning, ...]]:
        if self._roster is None or not candidates:
            return None, ()
        inns = [candidate.supplier.inn for candidate in candidates if candidate.supplier.inn]
        try:
            return await self._roster.roster(inns), ()
        except Exception:
            logger.warning("archive roster failed", exc_info=True)
            return None, (ARCHIVE_FAILED,)


def _with_novelty(
    candidates: Sequence[SupplierCandidate], roster: ArchiveRoster | None
) -> tuple[SupplierCandidate, ...]:
    if roster is None:
        return tuple(candidates)
    return tuple(
        dataclasses.replace(candidate, novelty=roster.novelty_of(candidate.supplier.inn))
        for candidate in candidates
    )
