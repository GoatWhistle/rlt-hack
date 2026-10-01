import os
from pathlib import Path

from src.adapter.repository.uploads.files import FileUploads
from src.service.upload.protocols import SearchEngine
from src.service.upload.worker import UploadService


def upload_service(search: SearchEngine) -> UploadService:
    return UploadService(search, FileUploads(Path(os.getenv("UPLOADS_DIR", "/data/uploads"))))
