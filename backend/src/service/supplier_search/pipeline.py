from collections.abc import Sequence

from src.models.enums import ItemOrigin, WarningCode
from src.models.match import MatchReport
from src.models.query_item import QueryItem, SearchRequest
from src.models.search import SearchQuery
from src.models.search_result import PipelineInfo, SearchWarning
from src.service.errors import UninterpretableQueryError
from src.service.supplier_search.matcher import SupplierMatcher
from src.service.supplier_search.protocols import Clock, QueryInterpreter
from src.service.supplier_search.settings import SearchSettings


def item_warnings(items: Sequence[QueryItem]) -> tuple[SearchWarning, ...]:
    if any(item.origin == ItemOrigin.INFERRED for item in items):
        return (SearchWarning(WarningCode.ITEMS_INFERRED),)
    return ()


class SearchPipeline:
    def __init__(
        self,
        interpreter: QueryInterpreter,
        matcher: SupplierMatcher,
        clock: Clock,
        settings: SearchSettings,
    ) -> None:
        self._interpreter = interpreter
        self._matcher = matcher
        self._clock = clock
        self._settings = settings

    async def run(self, query: SearchQuery) -> MatchReport:
        started_at = self._clock.now()
        items = await self._interpreter.interpret(query)
        if not items:
            raise UninterpretableQueryError
        outcome = await self._matcher.match(SearchRequest(query=query, items=items))
        context_used = any(
            channel in self._settings.context_channels for channel in outcome.channels
        )
        context = query.context.fields if context_used else ()
        return MatchReport(
            items=items,
            candidates=outcome.candidates,
            pipeline=PipelineInfo(
                version=self._settings.pipeline_version,
                channels=outcome.channels,
                as_of=started_at,
                inputs=("text", *context),
            ),
            warnings=(*item_warnings(items), *outcome.warnings),
        )
