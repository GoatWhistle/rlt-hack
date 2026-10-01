from dataclasses import dataclass

DEFAULT_UPLOAD_MAX_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ApiSettings:
    title: str = "LOTIVE API"
    version: str = "0.1.0"
    docs_enabled: bool = True
    upload_max_bytes: int = DEFAULT_UPLOAD_MAX_BYTES
