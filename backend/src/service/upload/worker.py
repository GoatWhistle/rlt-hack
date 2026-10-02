import asyncio
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

DEFAULT_MAX_BACKLOG = 40


class UploadService:
    def __init__(
        self,
        search: SearchEngine,
        repository: UploadRepository,
        max_backlog: int = DEFAULT_MAX_BACKLOG,
        position_tokens: PositionTokenizer | None = None,
    ) -> None:
        if max_backlog < 1:
            raise ValueError(max_backlog)
        self._position_tokens = position_tokens
        self._search = search
        self._repository = repository
        self._refresh_lock = asyncio.Lock()
        self._max_backlog = max_backlog
        self._backlog = 0

    async def create(self, owner: str, filename: str, notices: list[Notice]) -> Upload:
        if not notices:
            raise NoValidLotsError
        if self._backlog and self._backlog + len(notices) > self._max_backlog:
            raise UploadQueueFullError(self._max_backlog)
        self._backlog += len(notices)
        try:
            lots = await self._recommend_notices(notices)
        finally:
            self._backlog -= len(notices)
        upload = Upload(
            uuid4().hex, owner, filename, datetime.now(UTC).isoformat(), lots, self._version()
        )
        await self._repository.save(upload)
        return upload

    async def get(self, owner: str, upload_id: str) -> Upload | None:
        upload = await self._repository.get(owner, upload_id)
        version = self._version()
        if upload is not None and version and upload.ranking_version != version:
            async with self._refresh_lock:
                upload = await self._repository.get(owner, upload_id)
                if upload is not None and upload.ranking_version != version:
                    lots = await self._recommend_notices([lot.notice for lot in upload.lots])
                    upload = replace(upload, lots=lots, ranking_version=version)
                    await self._repository.save(upload)
        if upload is None or not isinstance(self._search, CandidateEnrichment):
            return upload
        candidates = [candidate for lot in upload.lots for candidate in lot.candidates]
        enriched = iter(await self._search.enrich(candidates))
        return replace(
            upload,
            lots=[
                replace(
                    lot,
                    candidates=await relevant_evidence(
                        lot.notice.query_text,
                        [next(enriched) for _ in lot.candidates],
                        lot.notice.positions,
                        self._position_tokens,
                    ),
                )
                for lot in upload.lots
            ],
        )

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

    async def list(self, owner: str) -> list[Upload]:
        return await self._repository.list(owner)
