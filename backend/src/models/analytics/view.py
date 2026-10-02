"""То, что оператор видит поверх среза: задержка, предупреждения, внимание."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from src.models.analytics.slice import AnalyticsSlice


class AttentionCode(StrEnum):
    SOURCE_NEVER_RUN = "source_never_run"
    SOURCE_FAILED = "source_failed"
    SOURCE_STALE = "source_stale"
    NO_CATEGORY = "no_category"
    NO_VERIFIED_SELLER = "no_verified_seller"


@dataclass(frozen=True, slots=True)
class AttentionItem:
    code: AttentionCode
    source_id: UUID | None
    count: int
    total: int


@dataclass(frozen=True, slots=True)
class AnalyticsView:
    snapshot: AnalyticsSlice
    delay_seconds: int
    warnings: tuple[str, ...]
    attention: tuple[AttentionItem, ...]
    names: dict[str, str]
