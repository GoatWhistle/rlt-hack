import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from src.models.errors import NoValidLotsError, TooManyNoticeRowsError
from src.models.upload import LotRecommendation, Notice, Upload
from src.service.upload.protocols import (
    CandidateEnrichment,
    SearchEngine,
    SearchVersion,
    UploadRepository,
)

MAX_LOTS = 20


class UploadService:
    def __init__(self, search: SearchEngine, repository: UploadRepository) -> None:
        self._search = search
        self._repository = repository
        self._refresh_lock = asyncio.Lock()

    async def create(self, owner: str, filename: str, notices: list[Notice]) -> Upload:
        if not notices:
            raise NoValidLotsError
        if len(notices) > MAX_LOTS:
            raise TooManyNoticeRowsError(MAX_LOTS)
        lots = []
        for notice in notices:
            query = "\n".join(filter(None, (notice.title, notice.subject)))
            candidates = await self._search.search(query, 10)
            lots.append(LotRecommendation(notice, candidates))
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
                    lots = []
                    for lot in upload.lots:
                        query = "\n".join(filter(None, (lot.notice.title, lot.notice.subject)))
                        lots.append(
                            LotRecommendation(lot.notice, await self._search.search(query, 10))
                        )
                    upload = replace(upload, lots=lots, ranking_version=version)
                    await self._repository.save(upload)
        if upload is None or not isinstance(self._search, CandidateEnrichment):
            return upload
        candidates = [candidate for lot in upload.lots for candidate in lot.candidates]
        enriched = iter(await self._search.enrich(candidates))
        return replace(
            upload,
            lots=[
                replace(lot, candidates=[next(enriched) for _ in lot.candidates])
                for lot in upload.lots
            ],
        )

    def _version(self) -> str:
        return self._search.version if isinstance(self._search, SearchVersion) else ""

    async def list(self, owner: str) -> list[Upload]:
        return await self._repository.list(owner)
