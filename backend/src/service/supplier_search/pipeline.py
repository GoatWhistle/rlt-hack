from collections.abc import Sequence

from src.models.enums import ItemOrigin, SearchStage, WarningCode
from src.models.match import MatchReport
from src.models.query_item import QueryItem, SearchRequest
from src.models.search import SearchQuery
from src.models.search_result import PipelineInfo, SearchWarning
from src.service.errors import UninterpretableQueryError
from src.service.supplier_search.matcher import SupplierMatcher
from src.service.supplier_search.protocols import Clock, QueryInterpreter, StageTimer
from src.service.supplier_search.settings import SearchSettings
from src.service.supplier_search.timing import UntimedStages


def item_warnings(items: Sequence[QueryItem], truncated: bool) -> tuple[SearchWarning, ...]:
    warnings: list[SearchWarning] = []
    if any(item.origin == ItemOrigin.INFERRED for item in items):
        warnings.append(SearchWarning(WarningCode.ITEMS_INFERRED))
    if truncated:
        warnings.append(SearchWarning(WarningCode.ITEMS_TRUNCATED))
    return tuple(warnings)


class SearchPipeline:
    def __init__(
        self,
        interpreter: QueryInterpreter,
        matcher: SupplierMatcher,
        clock: Clock,
        settings: SearchSettings,
        stages: StageTimer | None = None,
    ) -> None:
        self._interpreter = interpreter
        self._matcher = matcher
        self._clock = clock
        self._settings = settings
        self._stages = stages or UntimedStages()

    async def run(self, query: SearchQuery) -> MatchReport:
        started_at = self._clock.now()
        with self._stages.stage(SearchStage.PARSE):
            parsed = await self._interpreter.interpret(query)
        if not parsed:
            raise UninterpretableQueryError
        items = parsed[: self._settings.max_items]
        outcome = await self._matcher.match(SearchRequest(query=query, items=items))
        return MatchReport(
            items=items,
            candidates=outcome.candidates,
            pipeline=PipelineInfo(
                version=self._settings.pipeline_version,
                channels=outcome.channels,
                as_of=started_at,
            ),
            warnings=(*item_warnings(items, len(parsed) > len(items)), *outcome.warnings),
            offers=outcome.offers,
        )
