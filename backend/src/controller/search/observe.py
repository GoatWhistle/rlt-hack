import hashlib
import logging
from collections import Counter

from src.controller.http.middleware.metrics import Metrics
from src.models.enums import CandidateStatus
from src.models.search.search_result import SearchResult

logger = logging.getLogger(__name__)


def log_search_request(text: str) -> None:
    logger.info(
        "search requested",
        extra={
            "text_length": len(text),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
    )


def report_search(registry: Metrics, result: SearchResult) -> None:
    statuses = Counter(candidate.status for candidate in result.candidates)
    warnings = [f"{warning.code}:{warning.subject}" for warning in result.warnings]
    logger.info(
        "search completed",
        extra={
            "search_id": str(result.search_id),
            "items": len(result.items),
            "candidates": len(result.candidates),
            "recommended": statuses[CandidateStatus.RECOMMENDED],
            "check": statuses[CandidateStatus.CHECK],
            "empty": not result.candidates,
            "warnings": warnings,
            "channels": list(result.pipeline.channels),
            "pipeline_version": result.pipeline.version,
        },
    )
    registry.count("search_requests_total")
    if not result.candidates:
        registry.count("search_empty_total")
    for status in CandidateStatus:
        registry.count("search_candidates_total", {"status": status.value}, statuses[status])
    for warning in result.warnings:
        labels = {"code": warning.code.value, "subject": warning.subject}
        registry.count("search_warnings_total", labels)
