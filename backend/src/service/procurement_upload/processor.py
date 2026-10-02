import asyncio

from src.models.enums import SearchOrigin, WarningCode
from src.models.lot_result import LotResult
from src.models.procurement import ProcurementLot
from src.models.search import CandidateLimit, SearchQuery, SearchText
from src.service.errors import LotNotArchivedError, UninterpretableQueryError
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
            context=lot.context,
            origin=SearchOrigin.UPLOAD,
        )
        try:
            result = await self._search.search(query)
        except UninterpretableQueryError:
            return LotResult.not_understood(lot.lot_id, self._clock.now())
        if any(warning.code == WarningCode.ARCHIVE_FAILED for warning in result.warnings):
            raise LotNotArchivedError(lot.lot_id)
        return LotResult.of_search(lot.lot_id, self._clock.now(), result)
