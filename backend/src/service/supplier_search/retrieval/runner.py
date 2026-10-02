import asyncio
import logging
from collections.abc import Sequence

from src.models.enums import WarningCode
from src.models.ranking.retrieval import RetrievalHits
from src.models.search.query_item import SearchRequest
from src.models.search.search_result import SearchWarning
from src.service.errors import SearchUnavailableError
from src.service.supplier_search.protocols import CandidateRetriever

logger = logging.getLogger(__name__)


async def _attempt(
    retriever: CandidateRetriever, request: SearchRequest, depth: int
) -> RetrievalHits | None:
    try:
        return await retriever.retrieve(request, depth)
    except Exception:
        logger.warning(
            "retrieval channel failed", extra={"channel": retriever.channel}, exc_info=True
        )
        return None


class ChannelRunner:
    def __init__(self, retrievers: Sequence[CandidateRetriever]) -> None:
        if not retrievers:
            raise ValueError("at least one retrieval channel is required")
        self._retrievers = tuple(retrievers)

    async def run(
        self, request: SearchRequest, depth: int
    ) -> tuple[tuple[RetrievalHits, ...], tuple[SearchWarning, ...]]:
        outcomes = await asyncio.gather(
            *(_attempt(retriever, request, depth) for retriever in self._retrievers)
        )
        failed = tuple(
            retriever.channel
            for retriever, outcome in zip(self._retrievers, outcomes, strict=True)
            if outcome is None
        )
        if len(failed) == len(self._retrievers):
            raise SearchUnavailableError(failed)
        succeeded = tuple(outcome for outcome in outcomes if outcome is not None)
        warnings = tuple(SearchWarning(WarningCode.CHANNEL_FAILED, channel) for channel in failed)
        return succeeded, warnings
