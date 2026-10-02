import os
from pathlib import Path

from src.adapter.repository.uploads.files import FileUploads
from src.service.normalizer.text import stems
from src.service.upload.protocols import SearchEngine
from src.service.upload.worker import DEFAULT_MAX_BACKLOG, UploadService


def upload_service(search: SearchEngine) -> UploadService:
    return UploadService(
        search,
        FileUploads(Path(os.getenv("UPLOADS_DIR", "/data/uploads"))),
        int(os.getenv("UPLOAD_MAX_BACKLOG", str(DEFAULT_MAX_BACKLOG))),
        position_tokens=stems,
    )
