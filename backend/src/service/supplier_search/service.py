import asyncio
import dataclasses
import logging
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from src.models.enums import ItemOrigin, WarningCode
from src.models.query_item import QueryItem, SearchRequest
from src.models.search import SearchQuery
from src.models.search_result import PipelineInfo, SearchResult, SearchSummary, SearchWarning
from src.service.errors import SearchNotFoundError, SearchTimeoutError, UninterpretableQueryError
from src.service.supplier_search.matcher import SupplierMatcher
from src.service.supplier_search.protocols import (
    Clock,
    IdGenerator,
    QueryInterpreter,
    SearchArchive,
)
from src.service.supplier_search.settings import SearchSettings

logger = logging.getLogger(__name__)


class SupplierSearchService:
    def __init__(
        self,
        interpreter: QueryInterpreter,
        matcher: SupplierMatcher,
        archive: SearchArchive,
        clock: Clock,
        ids: IdGenerator,
        settings: SearchSettings,
    ) -> None:
        self._interpreter = interpreter
        self._matcher = matcher
        self._archive = archive
        self._clock = clock
        self._ids = ids
        self._settings = settings

    async def search(self, query: SearchQuery) -> SearchResult:
        try:
            async with asyncio.timeout(self._settings.timeout_seconds):
                result = await self._run(query)
        except TimeoutError as error:
            raise SearchTimeoutError(self._settings.timeout_seconds) from error
        return await self._archived(result)

    async def get(self, search_id: UUID) -> SearchResult:
        result = await self._archive.get(search_id)
        if result is None:
            raise SearchNotFoundError(search_id)
        return result

    async def recent(self, limit: int) -> tuple[SearchSummary, ...]:
        return await self._archive.recent(limit)

    async def _run(self, query: SearchQuery) -> SearchResult:
        started_at = self._clock.now()
        items = await self._interpreter.interpret(query)
        if not items:
            raise UninterpretableQueryError
        outcome = await self._matcher.match(SearchRequest(query=query, items=items))
        return SearchResult(
            search_id=self._ids.new(),
            query=query,
            items=items,
            candidates=outcome.candidates,
            pipeline=self._pipeline(outcome.channels, started_at),
            created_at=started_at,
            warnings=(*_item_warnings(items), *outcome.warnings),
        )

    def _pipeline(self, channels: tuple[str, ...], as_of: datetime) -> PipelineInfo:
        return PipelineInfo(
            version=self._settings.pipeline_version,
            channels=channels,
            as_of=as_of,
        )

    async def _archived(self, result: SearchResult) -> SearchResult:
        try:
            async with asyncio.timeout(self._settings.archive_timeout_seconds):
                await self._archive.save(result)
        except Exception:
            logger.warning("search %s was not archived", result.search_id, exc_info=True)
            warning = SearchWarning(WarningCode.ARCHIVE_FAILED)
            return dataclasses.replace(result, warnings=(*result.warnings, warning))
        return result


def _item_warnings(items: Sequence[QueryItem]) -> tuple[SearchWarning, ...]:
    if any(item.origin == ItemOrigin.INFERRED for item in items):
        return (SearchWarning(WarningCode.ITEMS_INFERRED),)
    return ()
