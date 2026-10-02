from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from src.models.enums import EvidenceKind
from src.models.errors import InvalidEvidenceError

WEB_SCHEMES = frozenset({"http", "https"})


def is_web_url(value: str) -> bool:
    parts = urlsplit(value.strip())
    return parts.scheme.lower() in WEB_SCHEMES and bool(parts.netloc)


@dataclass(frozen=True, slots=True)
class Evidence:
    kind: EvidenceKind
    title: str
    url: str
    checked_at: datetime

    def __post_init__(self) -> None:
        if not is_web_url(self.url):
            raise InvalidEvidenceError("url must be an absolute http(s) address")
        if self.checked_at.tzinfo is None:
            raise InvalidEvidenceError("checked_at must carry a timezone")
        object.__setattr__(self, "url", self.url.strip())
        object.__setattr__(self, "title", " ".join(self.title.split()))
