from typing import Protocol

from src.models.upload import Notice, Upload


class UploadManager(Protocol):
    async def create(self, owner: str, filename: str, notices: list[Notice]) -> Upload: ...

    async def get(self, owner: str, upload_id: str) -> Upload | None: ...

    async def list(self, owner: str) -> list[Upload]: ...
