import asyncio
import logging
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from src.models.errors import NoValidLotsError
from src.models.operations.upload import LotRecommendation, Notice, Upload
from src.models.search.supplier_search import SupplierCandidate
from src.service.errors import UploadQueueFullError
from src.service.upload.evidence import relevant_evidence
from src.service.upload.protocols import (
    BatchNoticeSearchEngine,
    CandidateEnrichment,
    NoticeSearchEngine,
    PositionTokenizer,
    SearchEngine,
    SearchVersion,
    UploadRepository,
)

DEFAULT_MAX_BACKLOG = 5000
DEFAULT_CHUNK_LOTS = 16
DEFAULT_RETRY_DELAYS = (2.0, 5.0)

logger = logging.getLogger(__name__)


class UploadService:
    def __init__(
        self,
        search: SearchEngine,
        repository: UploadRepository,
        max_backlog: int = DEFAULT_MAX_BACKLOG,
        position_tokens: PositionTokenizer | None = None,
        chunk_lots: int = DEFAULT_CHUNK_LOTS,
        retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
    ) -> None:
        if max_backlog < 1:
            raise ValueError(max_backlog)
        if chunk_lots < 1:
            raise ValueError(chunk_lots)
        if any(delay < 0 for delay in retry_delays):
            raise ValueError(retry_delays)
        self._position_tokens = position_tokens
        self._search = search
        self._repository = repository
        self._processing_lock = asyncio.Lock()
        self._max_backlog = max_backlog
        self._chunk_lots = chunk_lots
        self._retry_delays = retry_delays
        self._pending: dict[str, int] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    async def create(self, owner: str, filename: str, notices: list[Notice]) -> Upload:
        if not notices:
            raise NoValidLotsError
        pending = sum(self._pending.values())
        if pending and pending + len(notices) > self._max_backlog:
            raise UploadQueueFullError(self._max_backlog)
        upload = Upload(
            uuid4().hex,
            owner,
            filename,
            datetime.now(UTC).isoformat(),
            [LotRecommendation(notice, processed=False) for notice in notices],
            self._version(),
        )
        self._pending[upload.upload_id] = len(notices)
        try:
            await self._repository.save(upload)
        except BaseException:
            self._pending.pop(upload.upload_id, None)
            raise
        self._schedule(upload)
        return upload

    async def get(self, owner: str, upload_id: str) -> Upload | None:
        upload = await self._repository.get(owner, upload_id)
        if upload is None:
            return None
        self._resume(upload, refresh=True)
        if not isinstance(self._search, CandidateEnrichment):
            return upload
        candidates = [
            candidate for lot in upload.lots if lot.processed for candidate in lot.candidates
        ]
        enriched = iter(await self._search.enrich(candidates))
        return replace(
            upload,
            lots=[
                replace(
                    lot,
                    candidates=await relevant_evidence(
                        lot.notice.query_text,
                        [
                            replace(next(enriched), purchases=candidate.purchases)
                            for candidate in lot.candidates
                        ],
                        lot.notice.positions,
                        self._position_tokens,
                    ),
                )
                if lot.processed
                else lot
                for lot in upload.lots
            ],
        )

    async def drain(self) -> None:
        while self._tasks:
            await asyncio.gather(*self._tasks)

    def _resume(self, upload: Upload, *, refresh: bool) -> None:
        waiting = sum(not lot.processed for lot in upload.lots)
        stale = refresh and self._stale(upload)
        if (waiting or stale) and upload.upload_id not in self._pending:
            self._pending[upload.upload_id] = waiting
            self._schedule(upload)

    def _schedule(self, upload: Upload) -> None:
        task = asyncio.create_task(self._process(upload.owner, upload.upload_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _process(self, owner: str, upload_id: str) -> None:
        try:
            async with self._processing_lock:
                upload = await self._repository.get(owner, upload_id)
                if upload is not None:
                    upload, fresh = await self._complete(upload)
                    if self._stale(upload):
                        await self._refresh(upload, fresh)
        except Exception as error:
            logger.warning("upload processing stopped", exc_info=error)
        finally:
            self._pending.pop(upload_id, None)

    async def _complete(self, upload: Upload) -> tuple[Upload, set[int]]:
        lots = list(upload.lots)
        waiting = [index for index, lot in enumerate(lots) if not lot.processed]
        self._pending[upload.upload_id] = len(waiting)
        for start in range(0, len(waiting), self._chunk_lots):
            chunk = waiting[start : start + self._chunk_lots]
            notices = [lots[index].notice for index in chunk]
            try:
                done = await self._recommend_retrying(notices)
            except Exception as error:
                logger.warning("upload chunk failed, lots marked failed", exc_info=error)
                done = [LotRecommendation(notice, failed=True) for notice in notices]
            for index, lot in zip(chunk, done, strict=True):
                lots[index] = lot
            self._pending[upload.upload_id] = len(waiting) - start - len(chunk)
            upload = replace(upload, lots=list(lots))
            await self._repository.save(upload)
        return upload, set(waiting)

    async def _refresh(self, upload: Upload, fresh: set[int]) -> None:
        lots = list(upload.lots)
        stale = [index for index in range(len(lots)) if index not in fresh]
        for start in range(0, len(stale), self._chunk_lots):
            chunk = stale[start : start + self._chunk_lots]
            try:
                done = await self._recommend_retrying([lots[index].notice for index in chunk])
            except Exception as error:
                logger.warning("upload refresh failed, previous results kept", exc_info=error)
                return
            for index, lot in zip(chunk, done, strict=True):
                lots[index] = lot
        await self._repository.save(replace(upload, lots=lots, ranking_version=self._version()))

    async def _recommend_retrying(self, notices: list[Notice]) -> list[LotRecommendation]:
        for delay in self._retry_delays:
            try:
                return await self._recommend_notices(notices)
            except Exception as error:
                logger.warning("upload chunk failed, retry in %s s", delay, exc_info=error)
            await asyncio.sleep(delay)
        return await self._recommend_notices(notices)

    async def _recommend_notices(self, notices: list[Notice]) -> list[LotRecommendation]:
        if isinstance(self._search, BatchNoticeSearchEngine):
            recommendations = await self._search.search_notices(notices, 10)
            return [
                LotRecommendation(
                    notice,
                    await relevant_evidence(
                        notice.query_text, candidates, notice.positions, self._position_tokens
                    ),
                )
                for notice, candidates in zip(notices, recommendations, strict=True)
            ]
        return [LotRecommendation(notice, await self._recommend(notice)) for notice in notices]

    async def _recommend(self, notice: Notice) -> list[SupplierCandidate]:
        if isinstance(self._search, NoticeSearchEngine):
            return await relevant_evidence(
                notice.query_text,
                await self._search.search_notice(notice, 10),
                notice.positions,
                self._position_tokens,
            )
        query = notice.query_text
        return await relevant_evidence(
            query, await self._search.search(query, 10), notice.positions, self._position_tokens
        )

    def _version(self) -> str:
        return self._search.version if isinstance(self._search, SearchVersion) else ""

    def _stale(self, upload: Upload) -> bool:
        version = self._version()
        return bool(version) and upload.ranking_version != version

    async def list(self, owner: str) -> list[Upload]:
        uploads = await self._repository.list(owner)
        for upload in uploads:
            self._resume(upload, refresh=False)
        return uploads
