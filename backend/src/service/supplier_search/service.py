import asyncio
import dataclasses
import logging
from uuid import UUID

from src.models.enums import WarningCode
from src.models.search import SearchQuery
from src.models.search_result import SearchResult, SearchSummary, SearchWarning
from src.service.errors import SearchNotFoundError, SearchTimeoutError
from src.service.supplier_search.pipeline import SearchPipeline
from src.service.supplier_search.protocols import IdGenerator, SearchArchive
from src.service.supplier_search.settings import SearchSettings

logger = logging.getLogger(__name__)


class SupplierSearchService:
    def __init__(
        self,
        pipeline: SearchPipeline,
        archive: SearchArchive,
        ids: IdGenerator,
        settings: SearchSettings,
    ) -> None:
        self._pipeline = pipeline
        self._archive = archive
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
        report = await self._pipeline.run(query)
        return SearchResult(
            search_id=self._ids.new(),
            query=query,
            items=report.items,
            candidates=report.candidates,
            pipeline=report.pipeline,
            created_at=report.pipeline.as_of,
            warnings=report.warnings,
        )

    async def _archived(self, result: SearchResult) -> SearchResult:
        try:
            async with asyncio.timeout(self._settings.archive_timeout_seconds):
                await self._archive.save(result)
        except Exception:
            logger.warning(
                "search was not archived",
                extra={"search_id": str(result.search_id)},
                exc_info=True,
            )
            warning = SearchWarning(WarningCode.ARCHIVE_FAILED)
            return dataclasses.replace(result, warnings=(*result.warnings, warning))
        return result
