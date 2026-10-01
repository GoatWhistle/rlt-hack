"""Итоги операций над сохранёнными позициями."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class EnrichmentResult:
    sources: int = 0
    offers: int = 0
    classified: int = 0
    normalizer_version: str = ""
    classifier_version: str = ""


@dataclass(frozen=True, slots=True)
class ReidentifyResult:
    """Итог перевода позиций на действующее правило ключа идентичности."""

    sources: int = 0
    offers: int = 0
    changed: int = 0
    merged: int = 0


@dataclass(frozen=True, slots=True)
class RegistryImportResult:
    """Итог загрузки выгрузки реестра МСП."""

    companies: int = 0
    registry_date: date | None = None
