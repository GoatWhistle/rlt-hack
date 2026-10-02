from collections.abc import Sequence

from src.models.candidate import SupplierCandidate
from src.models.enums import SearchStage
from src.models.match import MatchOutcome
from src.models.query_item import SearchRequest
from src.models.search_result import SearchWarning
from src.service.supplier_search.assembly.assembler import CandidateAssembler
from src.service.supplier_search.enrichment.loader import EnrichmentLoader
from src.service.supplier_search.fusion.candidate import FusedCandidate
from src.service.supplier_search.fusion.rrf import ReciprocalRankFusion
from src.service.supplier_search.policy.policy import CandidatePolicy
from src.service.supplier_search.protocols import (
    CandidateRetriever,
    OfferCatalog,
    PurchaseHistory,
    StageTimer,
    SupplierDirectory,
)
from src.service.supplier_search.ranking.ranker import CandidateRanker
from src.service.supplier_search.retrieval.runner import ChannelRunner
from src.service.supplier_search.settings import SearchSettings
from src.service.supplier_search.timing import UntimedStages


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
        stages: StageTimer | None = None,
    ) -> None:
        self._stages = stages or UntimedStages()
        self._channels = ChannelRunner(retrievers)
        self._enrichment = EnrichmentLoader(directory, offers, history, settings)
        self._fusion = fusion
        self._assembler = assembler
        self._policy = policy
        self._ranker = ranker
        self._settings = settings

    async def match(self, request: SearchRequest) -> MatchOutcome:
        depth = self._settings.retrieval_depth(request.query.limit.value)
        with self._stages.stage(SearchStage.CHANNELS):
            hits, channel_warnings = await self._channels.run(request, depth)
        fused = self._fusion.fuse(hits)[:depth]
        candidates, enrichment_warnings = await self._candidates(fused, request)
        return MatchOutcome(
            candidates=candidates,
            channels=tuple(channel.channel for channel in hits),
            warnings=(*channel_warnings, *enrichment_warnings),
        )

    async def _candidates(
        self, fused: Sequence[FusedCandidate], request: SearchRequest
    ) -> tuple[tuple[SupplierCandidate, ...], tuple[SearchWarning, ...]]:
        if not fused:
            return (), ()
        with self._stages.stage(SearchStage.ENRICH):
            enrichment, warnings = await self._enrichment.load(fused, request.items)
        with self._stages.stage(SearchStage.POLICY):
            drafts = (self._assembler.assemble(entry, request.items, enrichment) for entry in fused)
            judged = [
                (draft, self._policy.evaluate(draft)) for draft in drafts if draft is not None
            ]
            ranked = self._ranker.rank(judged, request.query.limit.value)
        return ranked, warnings
