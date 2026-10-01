from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from src.models.upload import LotRecommendation, Notice, Upload
from src.service.errors import ServiceError
from src.service.upload.protocols import CandidateEnrichment, SearchEngine, UploadRepository


class UploadService:
    def __init__(self, search: SearchEngine, repository: UploadRepository) -> None:
        self._search = search
        self._repository = repository

    async def create(self, owner: str, filename: str, notices: list[Notice]) -> Upload:
        if not notices or len(notices) > 20:
            raise ServiceError("в тестовом режиме загрузите от 1 до 20 закупок")
        lots = []
        for notice in notices:
            query = "\n".join(filter(None, (notice.title, notice.subject)))
            candidates = await self._search.search(query, 10)
            lots.append(LotRecommendation(notice, candidates))
        upload = Upload(uuid4().hex, owner, filename, datetime.now(UTC).isoformat(), lots)
        await self._repository.save(upload)
        return upload

    async def get(self, owner: str, upload_id: str) -> Upload | None:
        upload = await self._repository.get(owner, upload_id)
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

    async def list(self, owner: str) -> list[Upload]:
        return await self._repository.list(owner)
