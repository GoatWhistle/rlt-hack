import asyncio

from src.models.lot_result import LotResult
from src.models.procurement import ProcurementLot
from src.models.query_item import SearchRequest
from src.models.search import CandidateLimit, SearchQuery, SearchText
from src.service.procurement_upload.protocols import Clock, ItemInterpreter, LotMatching
from src.service.procurement_upload.settings import UploadSettings


class LotProcessor:
    def __init__(
        self,
        interpreter: ItemInterpreter,
        matcher: LotMatching,
        clock: Clock,
        settings: UploadSettings,
    ) -> None:
        self._interpreter = interpreter
        self._matcher = matcher
        self._clock = clock
        self._settings = settings

    async def process(self, lot: ProcurementLot) -> LotResult:
        async with asyncio.timeout(self._settings.lot_timeout_seconds):
            return await self._run(lot)

    async def _run(self, lot: ProcurementLot) -> LotResult:
        query = SearchQuery(
            text=SearchText(lot.search_text),
            limit=CandidateLimit(self._settings.candidates_per_lot),
        )
        items = await self._interpreter.interpret(query)
        if not items:
            return LotResult(lot_id=lot.lot_id, processed_at=self._clock.now())
        outcome = await self._matcher.match(SearchRequest(query=query, items=items))
        return LotResult(
            lot_id=lot.lot_id,
            processed_at=self._clock.now(),
            items=items,
            candidates=outcome.candidates,
            warnings=outcome.warnings,
        )
