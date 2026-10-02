"""Безопасное описание ошибки обхода для показа оператору."""

import re

MESSAGE_LIMIT = 240
_SECRET = re.compile(
    r"(?i)\b(token|key|secret|password|passwd|proxy|authorization|cookie)\b\s*[=:]\s*\S+"
)
_CREDENTIALS = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@")
_QUERY = re.compile(r"(https?://[^\s?#]+)\?\S+")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def safe_message(message: str) -> str:
    cleaned = _CREDENTIALS.sub(r"\1***@", message)
    cleaned = _SECRET.sub(lambda found: f"{found.group(1)}=***", cleaned)
    cleaned = _QUERY.sub(r"\1", cleaned)
    cleaned = _EMAIL.sub("***", cleaned)
    cleaned = " ".join(cleaned.split())
    if len(cleaned) <= MESSAGE_LIMIT:
        return cleaned
    return cleaned[: MESSAGE_LIMIT - 1].rstrip() + "…"
