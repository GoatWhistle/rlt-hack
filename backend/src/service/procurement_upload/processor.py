import asyncio

from src.models.lot_result import LotResult
from src.models.procurement import ProcurementLot
from src.models.search import CandidateLimit, SearchQuery, SearchText
from src.service.errors import UninterpretableQueryError
from src.service.procurement_upload.protocols import Clock, LotSearching
from src.service.procurement_upload.settings import UploadSettings


class LotProcessor:
    def __init__(self, search: LotSearching, clock: Clock, settings: UploadSettings) -> None:
        self._search = search
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
        try:
            report = await self._search.run(query)
        except UninterpretableQueryError:
            return LotResult(lot_id=lot.lot_id, processed_at=self._clock.now())
        return LotResult(
            lot_id=lot.lot_id,
            processed_at=self._clock.now(),
            items=report.items,
            candidates=report.candidates,
            warnings=report.warnings,
            pipeline=report.pipeline,
        )
