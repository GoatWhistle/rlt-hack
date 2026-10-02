"""Фильтры аналитики и политика свежести."""

from dataclasses import dataclass
from uuid import UUID

from src.models.enums import SourceType

DEFINITIONS_VERSION = "2026-10-02.1"


@dataclass(frozen=True, slots=True)
class AnalyticsFilters:
    """Регион относится к компании продавца, а не к региону поставки."""

    source_id: UUID | None = None
    source_type: SourceType | None = None
    region: str | None = None

    @property
    def scope_key(self) -> str:
        parts = (
            ("source", str(self.source_id) if self.source_id else ""),
            ("type", str(self.source_type) if self.source_type else ""),
            ("region", self.region or ""),
        )
        chosen = [f"{name}={value}" for name, value in parts if value]
        return "|".join(chosen) or "all"


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    """Порог свежести наблюдения в днях: реестр обновляется реже каталога."""

    offer_days: int = 7
    registry_days: int = 30
    period_days: int = 30
    version: str = "default-1"
